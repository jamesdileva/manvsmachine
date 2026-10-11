"""Profile endpoints + service tests (Sprint 22 — the §2.5 gap, live-verified)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.security import create_access_token
from app.db import models  # noqa: F401 — keeps table models importable for seeding
from app.db.connection import make_engine
from app.repositories.scoring import ScoringRepository
from app.repositories.user import UserRepository
from app.services.profile_service import ProfileService
from app.services.scoring_service import STREAK_CORRECT, STREAK_DAILY

CHALLENGE_ID = "challenge_slogan_01"


@pytest.fixture
def tmp_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / 'profile_test.db').as_posix()}"


@pytest.fixture
async def db_session(tmp_db_url: str) -> AsyncSession:
    engine: AsyncEngine = make_engine(tmp_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        session.add(
            models.Challenge(
                id=CHALLENGE_ID,
                name="Tiny Tagline",
                prompt="Write a slogan for a dragon-owned bakery.",
                ai_prompt_template_id="v1.0",
            )
        )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
def service(db_session: AsyncSession) -> ProfileService:
    return ProfileService(ScoringRepository(db_session), UserRepository(db_session))


async def _seed_user(session: AsyncSession, user_id: str, name: str, rating: float = 1000.0) -> models.User:
    user = models.User(id=user_id, display_name=name, guest_id=f"guest-{user_id}")
    user.detection_rating = rating
    session.add(user)
    await session.commit()
    return user


async def _seed_scored_round(
    session: AsyncSession,
    user_id: str,
    *,
    round_id: str,
    challenge_id: str = CHALLENGE_ID,
    vote_correct: bool = True,
    humanity: float | None = 68.0,
) -> models.Round:
    """One scored round with linked entries, score, and an optional humanity row."""
    game_session = models.Session(user_id=user_id, challenge_ids=[challenge_id], is_daily=True)
    session.add(game_session)
    await session.commit()
    rnd = models.Round(
        id=round_id,
        session_id=game_session.id,
        challenge_id=challenge_id,
        round_number=1,
        state="scored",
        reveal_data={"human_was": "A", "vote_correct": vote_correct},
    )
    session.add(rnd)
    await session.commit()
    human = models.Entry(round_id=rnd.id, author_type="human", content="Fire baked. Dragon approved.")
    ai = models.Entry(round_id=rnd.id, author_type="ai", content="Dragon's fire, fresh baked.")
    session.add(human)
    session.add(ai)
    await session.commit()
    rnd.human_entry_id = human.id
    rnd.ai_entry_id = ai.id
    await session.commit()
    session.add(
        models.Score(
            user_id=user_id,
            round_id=rnd.id,
            base_score=100 if vote_correct else 0,
            time_bonus=10,
            streak_bonus=0,
            total_score=110 if vote_correct else 10,
        )
    )
    if humanity is not None:
        session.add(
            models.HumanityScore(entry_id=human.id, humanity_score=humanity, total_votes=1)
        )
    await session.commit()
    return rnd


# ---------------------------------------------------------------------------
# ProfileService


async def test_profile_aggregates_every_stat(
    service: ProfileService, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, "alice", name="Player_1", rating=1012.5)
    await _seed_scored_round(db_session, "alice", round_id="r1", vote_correct=True)
    await _seed_scored_round(db_session, "alice", round_id="r2", vote_correct=True)
    await _seed_scored_round(
        db_session, "alice", round_id="r3", vote_correct=False, humanity=None
    )
    db_session.add(models.Streak(user_id="alice", type=STREAK_CORRECT, count=3, longest_record=7))
    db_session.add(models.Streak(user_id="alice", type=STREAK_DAILY, count=5, longest_record=9))
    await db_session.commit()

    profile = await service.get_profile("alice")

    assert profile.user_id == "alice"
    assert profile.display_name == "Player_1"
    assert profile.is_guest is True
    assert profile.detection_rating == 1012.5
    assert profile.total_rounds == 3
    assert profile.overall_accuracy == pytest.approx(66.666, abs=0.01)
    assert profile.current_streak == 3
    assert profile.longest_streak == 7
    assert profile.daily_challenge_streak == 5
    assert len(profile.recent_humanity_scores) == 2
    assert all(entry.challenge_id == CHALLENGE_ID for entry in profile.recent_humanity_scores)
    assert all(entry.score == 68 for entry in profile.recent_humanity_scores)


async def test_profile_for_a_new_guest(service: ProfileService, db_session: AsyncSession) -> None:
    await _seed_user(db_session, "fresh", name="Player_2")

    profile = await service.get_profile("fresh")

    assert profile.detection_rating == 1000.0
    assert profile.total_rounds == 0
    assert profile.overall_accuracy == 0.0
    assert profile.current_streak == 0
    assert profile.longest_streak == 0
    assert profile.daily_challenge_streak == 0
    assert profile.recent_humanity_scores == []


async def test_profile_rejects_unknown_users(service: ProfileService) -> None:
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await service.get_profile("nobody")


async def test_update_display_name(service: ProfileService, db_session: AsyncSession) -> None:
    await _seed_user(db_session, "renamer", name="Old")

    updated = await service.update_display_name("renamer", "DragonBakery")

    assert updated.display_name == "DragonBakery"
    profile = await service.get_profile("renamer")
    assert profile.display_name == "DragonBakery"


async def test_update_display_name_rejects_unknown_users(service: ProfileService) -> None:
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await service.update_display_name("nobody", "Nope")


# ---------------------------------------------------------------------------
# HTTP endpoints


def _client_with_user(tmp_db_url: str, user_id: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient against a DB pre-seeded with one user (tables already created)."""
    monkeypatch.setattr(settings, "database_url", tmp_db_url)
    from app import main

    return TestClient(main.app)


@pytest.fixture
def seeded_db(tmp_db_url: str) -> str:
    """Migrate the throwaway DB via the app's own path, then seed one player."""
    import asyncio

    from app.db import models as m
    from app.db.connection import run_migrations

    run_migrations(tmp_db_url)

    async def seed() -> None:
        engine: AsyncEngine = make_engine(tmp_db_url)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            session.add(
                m.Challenge(
                    id=CHALLENGE_ID,
                    name="Tiny Tagline",
                    prompt="Write a slogan for a dragon-owned bakery.",
                    ai_prompt_template_id="v1.0",
                )
            )
            await session.commit()
            await _seed_user(session, "http-user", name="Player_HTTP", rating=1007.7)
            await _seed_scored_round(session, "http-user", round_id="h1", vote_correct=True)
            await _seed_scored_round(session, "http-user", round_id="h2", vote_correct=True)
            session.add(m.Streak(user_id="http-user", type=STREAK_CORRECT, count=2, longest_record=4))
            await session.commit()
        await engine.dispose()

    asyncio.run(seed())
    return tmp_db_url


def test_get_profile_requires_auth(seeded_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with _client_with_user(seeded_db, "http-user", monkeypatch) as client:
        response = client.get("/api/v1/profile")
    assert response.status_code == 401


def test_put_profile_requires_auth(seeded_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with _client_with_user(seeded_db, "http-user", monkeypatch) as client:
        response = client.put("/api/v1/profile", json={"display_name": "Nope"})
    assert response.status_code == 401


def test_get_profile_http(seeded_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    token = create_access_token("http-user")
    with _client_with_user(seeded_db, "http-user", monkeypatch) as client:
        response = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["display_name"] == "Player_HTTP"
    assert body["detection_rating"] == 1007.7
    assert body["total_rounds"] == 2
    assert body["overall_accuracy"] == 100.0
    assert body["current_streak"] == 2
    assert body["longest_streak"] == 4
    assert len(body["recent_humanity_scores"]) == 2


def test_put_profile_http(seeded_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    token = create_access_token("http-user")
    with _client_with_user(seeded_db, "http-user", monkeypatch) as client:
        response = client.put(
            "/api/v1/profile",
            json={"display_name": "DragonBakery"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["display_name"] == "DragonBakery"
        again = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token}"})
    assert again.json()["display_name"] == "DragonBakery"
