"""VotingService tests (Sprint 11) — A/B presentation, vote processing, reveal."""

import random
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel

from app.core.exceptions import ConflictError, NotFoundError
from app.db import models  # noqa: F401 — registers tables on SQLModel.metadata
from app.db.connection import make_engine
from app.repositories.voting import VotingRepository
from app.services.humanity_scoring import HumanityScoring
from app.services.voting_service import VotingService

CHALLENGE_ID = "challenge_slogan_01"

HUMAN_TEXT = "Fire baked. Dragon approved."
AI_TEXT = "Dragon's fire, fresh baked."


@pytest.fixture
def tmp_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / 'voting_test.db').as_posix()}"


@pytest.fixture
async def db_session(tmp_db_url: str) -> AsyncSession:
    engine: AsyncEngine = make_engine(tmp_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def service(db_session: AsyncSession) -> VotingService:
    return VotingService(VotingRepository(db_session))


async def _seed_round(
    session: AsyncSession, round_id: str = "round-1", state: str = "writing", user_id: str = "user-1"
) -> models.Round:
    """A round with both entries present and linked (Sprint 3's seeding shape)."""
    user = models.User(id=user_id, display_name="Player_1", guest_id=f"guest-{user_id}")
    session.add(user)
    await session.commit()
    if await session.get(models.Challenge, CHALLENGE_ID) is None:
        session.add(
            models.Challenge(
                id=CHALLENGE_ID,
                name="Tiny Tagline",
                prompt="Write a slogan for a dragon-owned bakery.",
                ai_prompt_template_id="v1.0",
            )
        )
        await session.commit()
    game_session = models.Session(user_id=user.id, challenge_ids=[CHALLENGE_ID], is_daily=True)
    session.add(game_session)
    await session.commit()
    rnd = models.Round(
        id=round_id, session_id=game_session.id, challenge_id=CHALLENGE_ID, round_number=1, state=state
    )
    session.add(rnd)
    await session.commit()
    human = models.Entry(round_id=rnd.id, author_type="human", content=HUMAN_TEXT)
    ai = models.Entry(round_id=rnd.id, author_type="ai", content=AI_TEXT)
    session.add(human)
    session.add(ai)
    await session.commit()
    rnd.human_entry_id = human.id
    rnd.ai_entry_id = ai.id
    await session.commit()
    return rnd


# ---------------------------------------------------------------------------
# present_entries


async def test_present_entries_returns_anonymized_pair(service: VotingService, db_session: AsyncSession) -> None:
    await _seed_round(db_session)
    entries = await service.present_entries("round-1")
    assert set(entries) == {"A", "B"}
    assert sorted(entries.values()) == sorted([HUMAN_TEXT, AI_TEXT])


async def test_present_entries_marks_the_round_voting(service: VotingService, db_session: AsyncSession) -> None:
    await _seed_round(db_session)
    await service.present_entries("round-1")
    rnd = await db_session.get(models.Round, "round-1")
    assert rnd is not None and rnd.state == "voting"


async def test_present_entries_is_stable_per_round(service: VotingService, db_session: AsyncSession) -> None:
    await _seed_round(db_session)
    first = await service.present_entries("round-1")
    second = await service.present_entries("round-1")
    assert first == second


async def test_present_entries_differs_across_rounds(service: VotingService, db_session: AsyncSession) -> None:
    # Same entries in many rounds: the assignment must vary (seeded per round id).
    human_letters: set[str] = set()
    for i in range(20):
        await _seed_round(db_session, round_id=f"round-{i}", user_id=f"user-{i}")
        entries = await service.present_entries(f"round-{i}")
        human_letters.add("A" if entries["A"] == HUMAN_TEXT else "B")
    assert human_letters == {"A", "B"}


async def test_present_entries_unknown_or_empty_round(service: VotingService, db_session: AsyncSession) -> None:
    assert await service.present_entries("round-missing") == {}

    rnd = await _seed_round(db_session)
    rnd.human_entry_id = None
    await db_session.commit()
    assert await service.present_entries(rnd.id) == {}


# ---------------------------------------------------------------------------
# process_vote


async def test_process_vote_records_the_vote(service: VotingService, db_session: AsyncSession) -> None:
    await _seed_round(db_session)
    result = await service.process_vote("round-1", "user-1", "A")
    assert result.round_id == "round-1"
    assert result.vote == "A"
    assert result.can_reveal is True
    assert result.total_votes == 1

    rnd = await db_session.get(models.Round, "round-1")
    assert rnd is not None and rnd.vote == "A"
    votes = await service.repo.get_votes_for_round("round-1")
    assert len(votes) == 1 and votes[0].selected_entry == "A"


async def test_process_vote_rejects_invalid_letters(service: VotingService, db_session: AsyncSession) -> None:
    await _seed_round(db_session)
    with pytest.raises(ValueError):
        await service.process_vote("round-1", "user-1", "C")


async def test_process_vote_unknown_round(service: VotingService, db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await service.process_vote("round-missing", "user-1", "A")


async def test_process_vote_after_reveal_is_rejected(service: VotingService, db_session: AsyncSession) -> None:
    await _seed_round(db_session)
    await service.process_vote("round-1", "user-1", "A")
    await service.reveal("round-1")
    with pytest.raises(ConflictError):
        await service.process_vote("round-1", "user-1", "B")


# ---------------------------------------------------------------------------
# reveal


async def test_reveal_attributes_entries_and_scores_the_vote(
    service: VotingService, db_session: AsyncSession
) -> None:
    await _seed_round(db_session)
    entries = await service.present_entries("round-1")
    ai_letter = "B" if entries["A"] == HUMAN_TEXT else "A"
    await service.process_vote("round-1", "user-1", ai_letter)  # correctly identifies the AI

    reveal = await service.reveal("round-1")
    assert reveal.vote_correct is True
    assert reveal.vote == ai_letter
    assert reveal.entries[reveal.human_was] == HUMAN_TEXT
    assert reveal.entries[reveal.ai_was] == AI_TEXT
    assert {reveal.human_was, reveal.ai_was} == {"A", "B"}
    # The AI was detected: it gets no humanity credit; the human entry passes as human.
    assert reveal.humanity_ai == 0.0
    assert reveal.humanity_human == 100.0
    assert reveal.ai_was in reveal.explanation

    rnd = await db_session.get(models.Round, "round-1")
    assert rnd is not None and rnd.state == "scored"
    assert rnd.reveal_data["human_was"] == reveal.human_was
    assert rnd.reveal_data["vote_correct"] is True


async def test_reveal_when_the_ai_fools_the_player(
    service: VotingService, db_session: AsyncSession
) -> None:
    await _seed_round(db_session)
    entries = await service.present_entries("round-1")
    human_letter = "A" if entries["A"] == HUMAN_TEXT else "B"
    await service.process_vote("round-1", "user-1", human_letter)  # wrong guess

    reveal = await service.reveal("round-1")
    assert reveal.vote_correct is False
    assert reveal.humanity_ai == 100.0  # the AI fooled the player
    assert reveal.humanity_human == 0.0  # the player thought the human was the AI
    assert "fooled" in reveal.explanation.lower()


async def test_reveal_persists_humanity_scores(service: VotingService, db_session: AsyncSession) -> None:
    await _seed_round(db_session)
    entries = await service.present_entries("round-1")
    ai_letter = "B" if entries["A"] == HUMAN_TEXT else "A"
    await service.process_vote("round-1", "user-1", ai_letter)
    reveal = await service.reveal("round-1")

    rnd = await db_session.get(models.Round, "round-1")
    assert rnd is not None
    human_row = await db_session.get(models.HumanityScore, rnd.human_entry_id)
    ai_row = await db_session.get(models.HumanityScore, rnd.ai_entry_id)
    assert human_row is not None and human_row.humanity_score == 100.0
    assert ai_row is not None and ai_row.humanity_score == 0.0
    assert human_row.total_votes == 1 and ai_row.total_votes == 1


async def test_reveal_without_a_vote(service: VotingService, db_session: AsyncSession) -> None:
    await _seed_round(db_session, state="voting")
    reveal = await service.reveal("round-1")
    assert reveal.vote is None
    assert reveal.vote_correct is False
    assert reveal.humanity_human == 0.0  # no voters: no evidence of humanity
    assert reveal.humanity_ai == 0.0


async def test_reveal_unknown_round(service: VotingService, db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await service.reveal("round-missing")


async def test_reveal_twice_is_rejected(service: VotingService, db_session: AsyncSession) -> None:
    await _seed_round(db_session)
    await service.process_vote("round-1", "user-1", "A")
    await service.reveal("round-1")
    with pytest.raises(ConflictError):
        await service.reveal("round-1")


# ---------------------------------------------------------------------------
# HumanityScoring (Master Architecture §13.5)


def test_humanity_scoring_percentages() -> None:
    scoring = HumanityScoring()
    votes = [
        models.Vote(round_id="r", user_id="u1", selected_entry="B"),
        models.Vote(round_id="r", user_id="u2", selected_entry="B"),
        models.Vote(round_id="r", user_id="u3", selected_entry="A"),
    ]
    # Entry A: two of three voters picked B as the AI, i.e. guessed A was human.
    assert scoring.calculate(votes, "A") == pytest.approx(200 / 3)
    # Entry B: one of three picked A as the AI, i.e. guessed B was human.
    assert scoring.calculate(votes, "B") == pytest.approx(100 / 3)
    assert scoring.calculate([], "A") == 0.0


def test_assignment_seed_is_process_stable() -> None:
    # The seed derives from the round id only (no PYTHONHASHSEED dependency).
    first = random.Random("ab-assignment:round-1").random()
    second = random.Random("ab-assignment:round-1").random()
    assert first == second
