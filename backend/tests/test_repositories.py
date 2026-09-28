"""Repository tests (Sprint 3) — one test group per repository."""

import datetime as dt
import random
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings
from app.db import models  # noqa: F401 — registers tables on SQLModel.metadata
from app.db.connection import make_engine
from app.db.models import Challenge, Entry, Round, Score, Session, User, utc_now


@pytest.fixture
def tmp_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / 'repo_test.db').as_posix()}"


@pytest.fixture
async def db_session(tmp_db_url: str) -> AsyncSession:
    """Session bound to a throwaway DB with the full schema created."""
    engine: AsyncEngine = make_engine(tmp_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def monkeypatched_settings(tmp_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point settings at the throwaway DB (kept for parity with db tests)."""
    monkeypatch.setattr(settings, "database_url", tmp_db_url)


async def _seed_challenge(session: AsyncSession, challenge_id: str = "challenge_slogan_01") -> Challenge:
    challenge = Challenge(
        id=challenge_id,
        name="Tiny Tagline",
        prompt="Write a slogan for a dragon-owned bakery.",
        ai_prompt_template_id="v1.0",
    )
    session.add(challenge)
    await session.commit()
    return challenge


async def _seed_round_with_entries(session: AsyncSession) -> tuple[User, Session, Round, Entry, Entry]:
    user = User(display_name="Player_1", guest_id="guest-1")
    session.add(user)
    await session.commit()
    challenge = await _seed_challenge(session)
    game_session = Session(user_id=user.id, challenge_ids=[challenge.id], is_daily=True)
    session.add(game_session)
    await session.commit()
    rnd = Round(session_id=game_session.id, challenge_id=challenge.id, round_number=1)
    session.add(rnd)
    await session.commit()
    human = Entry(round_id=rnd.id, author_type="human", content="Fire baked. Dragon approved.")
    ai = Entry(round_id=rnd.id, author_type="ai", content="Where every loaf is forged in flame.")
    session.add(human)
    session.add(ai)
    await session.commit()
    rnd.human_entry_id = human.id
    rnd.ai_entry_id = ai.id
    await session.commit()
    return user, game_session, rnd, human, ai


# ---------------------------------------------------------------------------
# UserRepository


async def test_user_repository(db_session: AsyncSession) -> None:
    from app.repositories.user import UserRepository

    repo = UserRepository(db_session)

    guest = await repo.create_guest("Player_4829", guest_id="guest-abc")
    assert guest.id and guest.detection_rating == 1000.0
    assert (await repo.get_by_id(guest.id)) is not None
    assert await repo.get_by_id("missing-id") is None

    assert (await repo.get_by_guest_id("guest-abc")) is not None
    assert await repo.get_by_guest_id("missing-guest") is None

    updated = await repo.update_rating(guest.id, 1250.0)
    assert updated is not None and updated.detection_rating == 1250.0
    assert await repo.update_rating("missing-id", 5.0) is None

    renamed = await repo.update_display_name(guest.id, "Alex")
    assert renamed is not None and renamed.display_name == "Alex"
    assert await repo.update_display_name("missing-id", "X") is None


async def test_user_repository_leaderboard(db_session: AsyncSession) -> None:
    from app.repositories.user import UserRepository

    repo = UserRepository(db_session)
    for name, rating in [("Low", 900.0), ("Mid", 1000.0), ("High", 1500.0)]:
        user = await repo.create_guest(name)
        await repo.update_rating(user.id, rating)

    board = await repo.get_leaderboard()
    assert [entry.display_name for entry in board] == ["High", "Mid", "Low"]
    assert [entry.rank for entry in board] == [1, 2, 3]
    assert board[0].rating == 1500.0
    assert (await repo.get_leaderboard(limit=2))[0].display_name == "High"


# ---------------------------------------------------------------------------
# ChallengeRepository


async def test_challenge_repository(db_session: AsyncSession) -> None:
    from app.repositories.challenge import ChallengeRepository

    repo = ChallengeRepository(db_session)
    challenge = await _seed_challenge(db_session)

    assert (await repo.get_by_id(challenge.id)) is not None
    assert await repo.get_by_id("challenge_missing_99") is None

    await _seed_challenge(db_session, "challenge_caption_02")
    ids = await repo.get_all_ids()
    assert "challenge_slogan_01" in ids and "challenge_caption_02" in ids

    day = utc_now().date()
    assert await repo.get_daily(for_date=day) is None
    await repo.increment_daily_usage("challenge_slogan_01", for_date=day)
    daily = await repo.get_daily(for_date=day)
    assert daily is not None and daily.id == "challenge_slogan_01"
    # Deterministic: same date, same challenge.
    again = await repo.get_daily(for_date=day)
    assert again is not None and again.id == daily.id


# ---------------------------------------------------------------------------
# SessionRepository


async def test_session_repository(db_session: AsyncSession) -> None:
    from app.repositories.session import SessionRepository

    repo = SessionRepository(db_session)
    user, game_session, _, _, _ = await _seed_round_with_entries(db_session)

    created = await repo.create(user.id, ["challenge_slogan_01"], is_daily=True)
    assert created.is_daily and created.rounds_played == 0
    assert await repo.get("missing-session") is None

    completed = await repo.update_state(game_session.id, "completed")
    assert completed is not None and completed.completed_at is not None
    reopened = await repo.update_state(game_session.id, "in_progress")
    assert reopened is not None and reopened.completed_at is None
    with pytest.raises(ValueError):
        await repo.update_state(game_session.id, "bogus-state")
    assert await repo.update_state("missing-session", "completed") is None

    finished = await repo.complete(game_session.id, final_score=275)
    assert finished is not None and finished.final_score == 275
    assert finished.completed_at is not None


async def test_session_repository_recent_first(db_session: AsyncSession) -> None:
    from app.repositories.session import SessionRepository

    repo = SessionRepository(db_session)
    user, game_session, _, _, _ = await _seed_round_with_entries(db_session)
    older = Session(user_id=user.id, challenge_ids=[], started_at=utc_now() - dt.timedelta(hours=1))
    newer = Session(user_id=user.id, challenge_ids=[], started_at=utc_now() + dt.timedelta(hours=1))
    db_session.add(older)
    db_session.add(newer)
    await db_session.commit()

    recent = await repo.get_user_sessions(user.id, limit=2)
    assert [s.id for s in recent] == [newer.id, game_session.id]


# ---------------------------------------------------------------------------
# VotingRepository


async def test_voting_repository_votes(db_session: AsyncSession) -> None:
    from app.repositories.voting import VotingRepository

    repo = VotingRepository(db_session)
    user, _, rnd, _, _ = await _seed_round_with_entries(db_session)

    vote = await repo.create_vote(rnd.id, user.id, "A")
    assert vote is not None and vote.selected_entry == "A"
    stored_round = await db_session.get(Round, rnd.id)
    assert stored_round is not None and stored_round.vote == "A"  # denormalized onto the round

    with pytest.raises(ValueError):
        await repo.create_vote(rnd.id, user.id, "C")
    assert await repo.create_vote("missing-round", user.id, "A") is None

    votes = await repo.get_votes_for_round(rnd.id)
    assert len(votes) == 1
    assert await repo.get_votes_for_round("missing-round") == []


async def test_voting_repository_anonymized_entries(db_session: AsyncSession) -> None:
    from app.repositories.voting import VotingRepository

    repo = VotingRepository(db_session)
    _, _, rnd, human, ai = await _seed_round_with_entries(db_session)

    first = await repo.get_entries_anonymized(rnd.id, rng=random.Random(42))
    second = await repo.get_entries_anonymized(rnd.id, rng=random.Random(42))
    assert first == second  # seeded rng → deterministic assignment
    assert set(first) == {"A", "B"}
    assert set(first.values()) == {human.content, ai.content}

    assert await repo.get_entries_anonymized("missing-round") == {}


async def test_voting_repository_reveal(db_session: AsyncSession) -> None:
    from app.repositories.voting import VotingRepository

    repo = VotingRepository(db_session)
    _, _, rnd, _, _ = await _seed_round_with_entries(db_session)

    revealed = await repo.record_reveal(rnd.id, "A", {"humanity_human": 72})
    assert revealed is not None
    assert revealed.state == "scored"
    assert revealed.reveal_data["human_was"] == "A"
    assert revealed.reveal_data["humanity_human"] == 72
    with pytest.raises(ValueError):
        await repo.record_reveal(rnd.id, "Z")
    assert await repo.record_reveal("missing-round", "A") is None


# ---------------------------------------------------------------------------
# ScoringRepository


async def test_scoring_repository_daily_scores(db_session: AsyncSession) -> None:
    from app.repositories.scoring import ScoringRepository

    repo = ScoringRepository(db_session)
    user, game_session, rnd, _, _ = await _seed_round_with_entries(db_session)
    await repo.create_score(user.id, rnd.id, base=100, time_bonus=25, streak_bonus=10, total=135)

    other_user = User(display_name="Player_2")
    db_session.add(other_user)
    await db_session.commit()
    await repo.create_score(other_user.id, rnd.id, base=100, time_bonus=0, streak_bonus=0, total=200)

    yesterday = utc_now() - dt.timedelta(days=1)
    db_session.add(Score(user_id=user.id, round_id=rnd.id, base_score=100, time_bonus=0, streak_bonus=0, total_score=999, scored_at=yesterday))
    await db_session.commit()

    today = utc_now().date()
    board = await repo.get_daily_scores(for_date=today)
    assert [entry.display_name for entry in board] == ["Player_2", "Player_1"]
    assert board[0].score == 200 and board[0].rank == 1
    assert (await repo.get_daily_scores(for_date=today, limit=1))[0].display_name == "Player_2"


async def test_scoring_repository_rating_and_streaks(db_session: AsyncSession) -> None:
    from app.repositories.scoring import ScoringRepository

    repo = ScoringRepository(db_session)
    user, _, _, _, _ = await _seed_round_with_entries(db_session)

    assert await repo.get_user_rating(user.id) == 1000.0
    from app.repositories.user import UserRepository

    await UserRepository(db_session).update_rating(user.id, 1230.0)
    assert await repo.get_user_rating(user.id) == 1230.0
    assert await repo.get_user_rating("missing-user") == 1000.0

    streak = await repo.update_streak(user.id, "correct_guess", count=3)
    assert streak.count == 3 and streak.longest_record == 3
    streak = await repo.update_streak(user.id, "correct_guess", count=1)
    assert streak.count == 1 and streak.longest_record == 3  # longest is retained


# ---------------------------------------------------------------------------
# PromptAuditRepository


async def test_prompt_audit_repository(db_session: AsyncSession) -> None:
    from app.repositories.prompt_audit import PromptAuditRepository

    repo = PromptAuditRepository(db_session)
    await _seed_challenge(db_session)

    row = await repo.record(
        prompt_version="v1.0",
        prompt_system="You are a creative assistant...",
        prompt_user="Challenge: ...",
        challenge_id="challenge_slogan_01",
        ai_response="Fire baked. Dragon approved.",
        raw_response="Fire baked. Dragon approved.",
        provider="stub",
        model="stub-1",
        token_count=12,
    )
    assert row.id and row.recorded_at is not None
    assert len(await repo.get_by_challenge("challenge_slogan_01")) == 1
    assert await repo.get_by_challenge("challenge_missing_99") == []
    assert await repo.get_versions() == ["v1.0"]

    await repo.record(
        prompt_version="v1.1",
        prompt_system="...",
        prompt_user="...",
        challenge_id="challenge_slogan_01",
        ai_response="x",
        raw_response="x",
        provider="stub",
        model="stub-1",
    )
    assert await repo.get_versions() == ["v1.0", "v1.1"]
