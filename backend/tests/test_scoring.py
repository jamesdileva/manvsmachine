"""Scoring, rating, streak, and leaderboard tests (Sprint 12)."""

import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel, select

from app.core.config import settings
from app.db import models  # noqa: F401 — registers tables on SQLModel.metadata
from app.db.connection import make_engine
from app.db.models import utc_now
from app.repositories.scoring import ScoringRepository
from app.repositories.user import UserRepository
from app.schemas.challenge import ChallengeDefinition
from app.services.leaderboard_service import LeaderboardService
from app.services.scoring_service import ScoringService

CHALLENGE_ID = "challenge_slogan_01"


@pytest.fixture
def tmp_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / 'scoring_test.db').as_posix()}"


@pytest.fixture
async def db_session(tmp_db_url: str) -> AsyncSession:
    engine: AsyncEngine = make_engine(tmp_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    session_add = models.Challenge(
        id=CHALLENGE_ID,
        name="Tiny Tagline",
        prompt="Write a slogan for a dragon-owned bakery.",
        ai_prompt_template_id="v1.0",
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        session.add(session_add)
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
def service(db_session: AsyncSession) -> ScoringService:
    return ScoringService(ScoringRepository(db_session), UserRepository(db_session))


@pytest.fixture
def leaderboards(db_session: AsyncSession) -> LeaderboardService:
    return LeaderboardService(ScoringRepository(db_session), UserRepository(db_session))


@pytest.fixture
def challenge() -> ChallengeDefinition:
    path = Path(__file__).resolve().parents[1] / "app" / "data" / "challenge_library" / f"{CHALLENGE_ID}.json"
    return ChallengeDefinition.model_validate_json(path.read_text(encoding="utf-8"))


async def _seed_user(session: AsyncSession, user_id: str, rating: float = 1000.0) -> models.User:
    user = models.User(id=user_id, display_name=user_id.title(), guest_id=f"guest-{user_id}")
    user.detection_rating = rating
    session.add(user)
    await session.commit()
    return user


async def _seed_round_with_score(
    session: AsyncSession,
    user_id: str,
    *,
    base: int = 100,
    total: int = 100,
    scored_at: dt.datetime | None = None,
    round_id: str = "round-1",
    vote_correct: bool = True,
    state: str = "scored",
    link_entries: bool = False,
) -> models.Round:
    game_session = models.Session(user_id=user_id, challenge_ids=[CHALLENGE_ID], is_daily=True)
    session.add(game_session)
    await session.commit()
    rnd = models.Round(
        id=round_id,
        session_id=game_session.id,
        challenge_id=CHALLENGE_ID,
        round_number=1,
        state=state,
        reveal_data={"human_was": "A", "vote_correct": vote_correct},
    )
    session.add(rnd)
    await session.commit()
    if link_entries:
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
            base_score=base,
            time_bonus=0,
            streak_bonus=0,
            total_score=total,
            scored_at=scored_at or utc_now(),
        )
    )
    await session.commit()
    return rnd


# ---------------------------------------------------------------------------
# calculate_round_score (Master Architecture §12.5)


async def test_round_score_matches_the_formula(service: ScoringService, challenge: ChallengeDefinition) -> None:
    result = service.calculate_round_score(True, 5, 15, 2, challenge)
    assert result.base == 100
    assert result.time_bonus == 5  # 100 * 0.15 * (5/15)
    assert result.streak_bonus == 10  # 2 * 100 * 0.05
    assert result.total == 115
    assert result.vote_correct is True

    wrong = service.calculate_round_score(False, 5, 15, 2, challenge)
    assert wrong.base == 0  # the guess component is zero; speed/streak still count
    assert wrong.total == 15


async def test_round_score_zero_time_remaining(service: ScoringService, challenge: ChallengeDefinition) -> None:
    result = service.calculate_round_score(True, 0, 15, 0, challenge)
    assert result.total == 100
    assert result.time_bonus == 0


# ---------------------------------------------------------------------------
# Detection Rating (GDD §6.2, ELO-style)


def test_rating_change_is_symmetric_at_parity(service: ScoringService) -> None:
    # humanity 50 -> AI rating 1000, equal to the player's default rating:
    # expected = 0.5, so a correct guess gains K/2 and a wrong guess loses K/2.
    assert service.calculate_rating_change(1000.0, 50.0, True, k=16.0) == pytest.approx(8.0)
    assert service.calculate_rating_change(1000.0, 50.0, False, k=16.0) == pytest.approx(-8.0)


def test_rating_change_rewards_detecting_deceptive_ai(service: ScoringService) -> None:
    easy = service.calculate_rating_change(1000.0, 0.0, True, k=16.0)
    hard = service.calculate_rating_change(1000.0, 100.0, True, k=16.0)
    assert hard > easy > 0  # catching a high-humanity AI is worth more

    easy_miss = service.calculate_rating_change(1000.0, 0.0, False, k=16.0)
    hard_miss = service.calculate_rating_change(1000.0, 100.0, False, k=16.0)
    assert easy_miss < hard_miss < 0  # missing an obvious AI hurts more


async def test_update_detection_rating_moves_both_ways(
    service: ScoringService, db_session: AsyncSession
) -> None:
    user = await _seed_user(db_session, "alice")
    new_rating = await service.update_detection_rating(user.id, True, 50.0)
    assert new_rating > 1000.0  # correct guess increases (K=32 for a new player)
    assert await service.repo.get_user_rating(user.id) == new_rating

    dropped = await service.update_detection_rating(user.id, False, 50.0)
    assert dropped < new_rating


async def test_update_detection_rating_uses_k16_after_50_rounds(
    service: ScoringService, db_session: AsyncSession
) -> None:
    user = await _seed_user(db_session, "veteran")
    for i in range(50):
        await _seed_round_with_score(
            db_session, user.id, round_id=f"round-{i}", total=100, base=100
        )
    change = await service.update_detection_rating(user.id, True, 50.0)
    assert change == pytest.approx(1008.0)  # K=16, parity expected 0.5 -> +8 (not the new-player 32)


async def test_update_detection_rating_has_a_floor(
    service: ScoringService, db_session: AsyncSession
) -> None:
    user = await _seed_user(db_session, "unlucky")
    rating = user.detection_rating
    for _ in range(10):
        rating = await service.update_detection_rating(user.id, False, 0.0)
    assert rating >= 100.0


# ---------------------------------------------------------------------------
# Humanity scores (Master Architecture §13.5)


async def test_update_humanity_score_from_votes(service: ScoringService, db_session: AsyncSession) -> None:
    await _seed_user(db_session, "bob")
    rnd = await _seed_round_with_score(db_session, "bob", round_id="round-h", link_entries=True)
    votes = [models.Vote(round_id=rnd.id, user_id="bob", selected_entry="A")]  # picked A as the AI

    # reveal_data says the human entry was A, so the human entry reads as machine-made.
    human_score = await service.update_humanity_score(rnd.human_entry_id, votes, is_ai=False)
    assert human_score == 0.0
    ai_score = await service.update_humanity_score(rnd.ai_entry_id, votes, is_ai=True)
    assert ai_score == 100.0  # the AI entry was guessed human

    human_row = await db_session.get(models.HumanityScore, rnd.human_entry_id)
    assert human_row is not None and human_row.humanity_score == 0.0
    ai_row = await db_session.get(models.HumanityScore, rnd.ai_entry_id)
    assert ai_row is not None and ai_row.total_votes == 1


async def test_update_humanity_score_before_reveal_is_zero(
    service: ScoringService, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, "carol")
    rnd = await _seed_round_with_score(
        db_session, "carol", round_id="round-nr", state="writing", link_entries=True
    )
    rnd.reveal_data = {}
    await db_session.commit()
    score = await service.update_humanity_score(rnd.human_entry_id, [], is_ai=False)
    assert score == 0.0
    assert await db_session.get(models.HumanityScore, rnd.human_entry_id) is None


# ---------------------------------------------------------------------------
# Streaks (GDD §6.3)


async def test_correct_guess_streak_accumulates_and_resets(
    service: ScoringService, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, "dave")
    assert await service.update_streak("dave", "correct_guess", True) == 1
    assert await service.update_streak("dave", "correct_guess", True) == 2
    assert await service.update_streak("dave", "correct_guess", False) == 0
    assert await service.update_streak("dave", "correct_guess", True) == 1
    assert await service.get_current_streak("dave", "correct_guess") == 1
    assert await service.get_current_streak("dave", "no_such_streak") == 0


async def test_daily_streak_counts_consecutive_days_and_resets_on_gaps(
    service: ScoringService, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, "erin")
    today = utc_now().date()
    yesterday = today - dt.timedelta(days=1)

    # First play today.
    assert await service.update_streak("erin", "daily_challenge", True) == 1
    # Same day again: unchanged.
    assert await service.update_streak("erin", "daily_challenge", True) == 1
    # Yesterday's streak continues.
    streak = (
        await db_session.execute(select(models.Streak).where(models.Streak.user_id == "erin"))
    ).scalars().one()
    streak.last_active_date = yesterday
    await db_session.commit()
    assert await service.update_streak("erin", "daily_challenge", True) == 2
    # A three-day gap resets to 1.
    streak.last_active_date = today - dt.timedelta(days=3)
    await db_session.commit()
    assert await service.update_streak("erin", "daily_challenge", True) == 1


async def test_daily_streak_goes_stale(service: ScoringService, db_session: AsyncSession) -> None:
    await _seed_user(db_session, "frank")
    streak = models.Streak(
        user_id="frank",
        type="daily_challenge",
        count=5,
        last_active_date=utc_now().date() - dt.timedelta(days=3),
    )
    db_session.add(streak)
    await db_session.commit()
    assert await service.get_current_streak("frank", "daily_challenge") == 0


# ---------------------------------------------------------------------------
# LeaderboardService (GDD §6.4)


async def test_daily_leaderboard_ranks_by_score_with_accuracy(
    leaderboards: LeaderboardService, db_session: AsyncSession
) -> None:
    today = utc_now()
    yesterday = today - dt.timedelta(days=1)

    await _seed_user(db_session, "gina")
    await _seed_round_with_score(db_session, "gina", base=100, total=300, scored_at=today)
    await _seed_round_with_score(db_session, "gina", base=0, total=0, scored_at=today, round_id="round-g2")
    await _seed_round_with_score(db_session, "gina", base=100, total=50, scored_at=yesterday, round_id="round-g3")

    await _seed_user(db_session, "hank")
    await _seed_round_with_score(
        db_session, "hank", base=100, total=200, scored_at=today, round_id="round-h1"
    )

    board = await leaderboards.get_daily_leaderboard(today.date())
    assert [entry.display_name for entry in board] == ["Gina", "Hank"]
    assert [entry.rank for entry in board] == [1, 2]
    assert [entry.score for entry in board] == [300, 200]
    assert board[0].accuracy == pytest.approx(50.0)  # 1 of 2 rounds correct today
    assert board[1].accuracy == pytest.approx(100.0)
    assert await leaderboards.get_daily_leaderboard(yesterday.date())  # still queryable by date


async def test_all_time_leaderboard_ranks_by_rating_with_accuracy(
    leaderboards: LeaderboardService, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, "ivy", rating=1200.0)
    await _seed_round_with_score(db_session, "ivy", round_id="round-i1", vote_correct=True)
    await _seed_round_with_score(db_session, "ivy", round_id="round-i2", vote_correct=True)

    await _seed_user(db_session, "jack", rating=1100.0)
    await _seed_round_with_score(db_session, "jack", round_id="round-j1", vote_correct=False)

    board = await leaderboards.get_all_time_leaderboard()
    assert [entry.display_name for entry in board] == ["Ivy", "Jack"]
    assert [entry.rating for entry in board] == [1200.0, 1100.0]
    assert board[0].accuracy == pytest.approx(100.0)
    assert board[1].accuracy == pytest.approx(0.0)


async def test_snapshot_is_idempotent(
    leaderboards: LeaderboardService, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, "kim")
    await _seed_round_with_score(db_session, "kim", total=150)
    today = utc_now().date()

    first = await leaderboards.generate_snapshot(today)
    assert [entry.rank for entry in first] == [1]

    await _seed_round_with_score(db_session, "kim", total=50, round_id="round-k2")
    second = await leaderboards.generate_snapshot(today)
    assert second[0].score == 200

    rows = (
        await db_session.execute(
            select(models.LeaderboardSnapshot).where(models.LeaderboardSnapshot.date == today)
        )
    ).scalars().all()
    assert len(rows) == 1  # no duplicates after regeneration


# ---------------------------------------------------------------------------
# Endpoints (Implementation Guide §2.4)


def _api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> object:
    db_file = tmp_path / "leaderboard_api.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    from app import main

    return main.app


def test_leaderboard_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    app = _api_client(tmp_path, monkeypatch)
    with TestClient(app) as client:
        guest = client.post("/api/v1/auth/guest", json={}).json()
        headers = {"Authorization": f"Bearer {guest['token']}"}

        maker = async_sessionmaker(
            make_engine(f"sqlite+aiosqlite:///{(tmp_path / 'leaderboard_api.db').as_posix()}"),
            expire_on_commit=False,
        )

        async def seed() -> None:
            async with maker() as session:
                game_session = models.Session(user_id=guest["user_id"], challenge_ids=[CHALLENGE_ID], is_daily=True)
                session.add(game_session)
                await session.commit()
                rnd = models.Round(
                    session_id=game_session.id, challenge_id=CHALLENGE_ID, round_number=1,
                    state="scored", reveal_data={"human_was": "A", "vote_correct": True},
                )
                session.add(rnd)
                await session.commit()
                session.add(
                    models.Score(
                        user_id=guest["user_id"], round_id=rnd.id, base_score=100,
                        time_bonus=10, streak_bonus=0, total_score=110,
                    )
                )
                await session.commit()

        import asyncio

        asyncio.run(seed())

        daily = client.get("/api/v1/leaderboard/daily", headers=headers)
        assert daily.status_code == 200, daily.text
        body = daily.json()
        assert body["date"] == utc_now().date().isoformat()
        assert len(body["entries"]) == 1
        assert body["entries"][0]["score"] == 110
        assert body["entries"][0]["accuracy"] == 100.0
        assert body["entries"][0]["rank"] == 1

        empty = client.get("/api/v1/leaderboard/daily?date=2020-01-01")
        assert empty.status_code == 200 and empty.json()["entries"] == []

        all_time = client.get("/api/v1/leaderboard/all-time", headers=headers)
        assert all_time.status_code == 200
        assert len(all_time.json()["entries"]) >= 1
        assert all_time.json()["entries"][0]["rating"] == 1000.0
