"""SessionService tests (Sprint 13) — state machine, round lifecycle, session flow."""

import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel, select

from app.core.config import settings
from app.core.exceptions import ConflictError, ConstraintViolationError, NotFoundError
from app.db import models  # noqa: F401 — registers tables on SQLModel.metadata
from app.db.connection import make_engine
from app.repositories.challenge import ChallengeRepository
from app.repositories.prompt_audit import PromptAuditRepository
from app.repositories.scoring import ScoringRepository
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.repositories.voting import VotingRepository
from app.services.ai.providers.stub_provider import StubProvider
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService, sync_library_to_db
from app.services.content_filter import ContentFilter
from app.services.prompt_audit_service import PromptAuditService
from app.services.scoring_service import ScoringService
from app.services.session_service import SessionService
from app.services.voting_service import VotingService

VALID_ENTRY = "Fire baked. Dragon approved."


@pytest.fixture
def tmp_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / 'session_test.db').as_posix()}"


@pytest.fixture
async def db_session(tmp_db_url: str) -> AsyncSession:
    engine: AsyncEngine = make_engine(tmp_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await sync_library_to_db(session)  # all 25 challenges: rounds FK to challenges
        session.add(models.User(id="user-1", display_name="Player_1", guest_id="guest-1"))
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
def service(db_session: AsyncSession) -> SessionService:
    challenge_service = ChallengeService(ChallengeRepository(db_session))
    ai_service = AIService(
        settings,
        ContentFilter(),
        PromptAuditService(PromptAuditRepository(db_session)),
        providers=[StubProvider()],
    )
    return SessionService(
        SessionRepository(db_session),
        challenge_service,
        ai_service,
        VotingService(VotingRepository(db_session)),
        ScoringService(ScoringRepository(db_session), UserRepository(db_session)),
    )


# ---------------------------------------------------------------------------
# start_session + state machine


async def test_start_session_queues_the_daily_pool(service: SessionService) -> None:
    game_session = await service.start_session("user-1", "daily")
    assert game_session.is_daily is True
    assert len(game_session.challenge_ids) == 3
    assert game_session.rounds_played == 0

    current = await service.start_next_round(game_session.id, "user-1")
    assert current is not None
    assert current.round_number == 1
    assert current.state == "writing"
    assert current.challenge.id == game_session.challenge_ids[0]
    assert current.rounds_total == 3


async def test_start_session_practice_explicit_and_random(service: SessionService) -> None:
    explicit = await service.start_session(
        "user-1", "practice", ["challenge_slogan_01", "challenge_emoji_03", "challenge_tweet_09"]
    )
    assert explicit.challenge_ids == ["challenge_slogan_01", "challenge_emoji_03", "challenge_tweet_09"]
    assert explicit.is_daily is False

    random_session = await service.start_session("user-1", "practice")
    assert len(random_session.challenge_ids) == 3
    assert len(set(random_session.challenge_ids)) == 3


async def test_start_session_rejects_unknown_challenges(service: SessionService) -> None:
    with pytest.raises(NotFoundError):
        await service.start_session("user-1", "practice", ["challenge_missing_99"])


async def test_transition_round_validates_the_state_machine(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session = await service.start_session("user-1", "daily")
    round_id = (await service.start_next_round(game_session.id, "user-1")).round_id

    assert await service.transition_round(round_id, "reveal_ai") is True
    assert await service.get_round_state(round_id) == "reveal_ai"
    assert await service.transition_round(round_id, "voting") is True
    assert await service.transition_round(round_id, "scored") is True
    assert await service.get_round_state(round_id) == "scored"


async def test_transition_round_rejects_invalid_transitions(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session = await service.start_session("user-1", "daily")
    round_id = (await service.start_next_round(game_session.id, "user-1")).round_id

    # WRITING -> SCORE without VOTE is rejected (sprint acceptance criterion).
    assert await service.transition_round(round_id, "scored") is False
    assert await service.get_round_state(round_id) == "writing"
    assert await service.transition_round(round_id, "voting") is False  # must pass through reveal_ai

    await service.transition_round(round_id, "reveal_ai")
    await service.transition_round(round_id, "voting")
    await service.transition_round(round_id, "scored")
    assert await service.transition_round(round_id, "writing") is False  # terminal


async def test_transition_round_unknown_round(service: SessionService) -> None:
    assert await service.transition_round("round-missing", "reveal_ai") is False
    assert await service.get_round_state("round-missing") == ""


# ---------------------------------------------------------------------------
# submit_entry


async def test_submit_entry_creates_both_entries_and_presents(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session = await service.start_session("user-1", "daily")
    current = await service.start_next_round(game_session.id, "user-1")

    submission = await service.submit_entry(current.round_id, VALID_ENTRY, "user-1")
    assert set(submission.entries) == {"A", "B"}
    assert VALID_ENTRY in submission.entries.values()
    assert submission.ai_provider == "stub"
    assert submission.ai_model == "stub-v1"
    assert submission.hard_violations == []
    assert await service.get_round_state(current.round_id) == "voting"

    # Both entries are persisted and linked to the round.
    round_row = await db_session.get(models.Round, current.round_id)
    assert round_row is not None and round_row.human_entry_id and round_row.ai_entry_id
    assert round_row.time_spent_seconds is not None
    human = await db_session.get(models.Entry, round_row.human_entry_id)
    ai = await db_session.get(models.Entry, round_row.ai_entry_id)
    assert human is not None and human.content == VALID_ENTRY and human.author_type == "human"
    assert ai is not None and ai.author_type == "ai"


async def test_submit_entry_blocks_hard_violations(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session = await service.start_session("user-1", "daily")
    # Round 1 of a daily pool may vary; use an explicit slogan challenge for the constraint.
    game_session = await service.start_session("user-1", "practice", ["challenge_slogan_01"])
    current = await service.start_next_round(game_session.id, "user-1")

    with pytest.raises(ConstraintViolationError) as excinfo:
        await service.submit_entry(current.round_id, "too many words in this entry friend sorry", "user-1")
    assert excinfo.value.status_code == 400
    assert any("too many words" in v for v in excinfo.value.violations)

    # No entries were created and the round is still writable.
    round_row = await db_session.get(models.Round, current.round_id)
    assert round_row is not None and round_row.human_entry_id is None
    assert round_row.state == "writing"


async def test_submit_entry_rejects_wrong_state(service: SessionService) -> None:
    game_session = await service.start_session("user-1", "daily")
    current = await service.start_next_round(game_session.id, "user-1")
    await service.submit_entry(current.round_id, VALID_ENTRY, "user-1")
    with pytest.raises(ConflictError):
        await service.submit_entry(current.round_id, "again?", "user-1")


async def test_submit_entry_rejects_empty_entry(service: SessionService) -> None:
    game_session = await service.start_session("user-1", "practice", ["challenge_slogan_01"])
    current = await service.start_next_round(game_session.id, "user-1")
    with pytest.raises(ConstraintViolationError):
        await service.submit_entry(current.round_id, "   ", "user-1")


async def test_submit_entry_unknown_round(service: SessionService) -> None:
    with pytest.raises(NotFoundError):
        await service.submit_entry("round-missing", VALID_ENTRY, "user-1")


async def test_complete_round_guards(service: SessionService) -> None:
    with pytest.raises(NotFoundError):
        await service.complete_round("round-missing")
    game_session = await service.start_session("user-1", "daily")
    current = await service.start_next_round(game_session.id, "user-1")
    with pytest.raises(ConflictError):  # not scored yet
        await service.complete_round(current.round_id)


async def test_transition_round_rejects_unknown_states(service: SessionService) -> None:
    game_session = await service.start_session("user-1", "daily")
    current = await service.start_next_round(game_session.id, "user-1")
    assert await service.transition_round(current.round_id, "bogus") is False


# ---------------------------------------------------------------------------
# vote: reveal + score + rating + streaks


async def _start_round_with_entry(service: SessionService, entry: str = VALID_ENTRY) -> tuple[models.Session, object]:
    game_session = await service.start_session("user-1", "daily")
    current = await service.start_next_round(game_session.id, "user-1")
    await service.submit_entry(current.round_id, entry, "user-1")
    return game_session, current


async def test_vote_scores_a_correct_guess(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session, current = await _start_round_with_entry(service)
    ai_letter = "B" if (await service.voting.present_entries(current.round_id))["A"] == VALID_ENTRY else "A"

    result = await service.vote(current.round_id, "user-1", ai_letter)
    assert result.reveal.vote_correct is True
    assert result.score.base == 100
    assert result.score.total == 100 + result.score.time_bonus + result.score.streak_bonus
    assert result.rating > 1000.0
    assert result.streak == 1

    # The score row, the round completion, and the session counter all moved.
    scores = (
        await db_session.execute(
            select(models.Score).where(models.Score.round_id == current.round_id)
        )
    ).scalars().all()
    assert len(scores) == 1 and scores[0].total_score == result.score.total
    round_row = await db_session.get(models.Round, current.round_id)
    assert round_row is not None and round_row.state == "scored" and round_row.completed_at is not None
    updated = await db_session.get(models.Session, game_session.id)
    assert updated is not None and updated.rounds_played == 1


async def test_vote_scores_a_wrong_guess(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session, current = await _start_round_with_entry(service)
    ai_letter = "B" if (await service.voting.present_entries(current.round_id))["A"] == VALID_ENTRY else "A"

    result = await service.vote(current.round_id, "user-1", "A" if ai_letter == "B" else "B")
    assert result.reveal.vote_correct is False
    assert result.score.base == 0
    assert result.rating < 1000.0
    assert result.streak == 0  # a wrong guess resets the correct streak


async def test_vote_updates_the_daily_streak_for_daily_sessions(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session, current = await _start_round_with_entry(service)
    ai_letter = "B" if (await service.voting.present_entries(current.round_id))["A"] == VALID_ENTRY else "A"
    await service.vote(current.round_id, "user-1", ai_letter)

    streaks = (
        await db_session.execute(
            select(models.Streak).where(models.Streak.user_id == "user-1")
        )
    ).scalars().all()
    by_type = {streak.type: streak.count for streak in streaks}
    assert by_type == {"correct_guess": 1, "daily_challenge": 1}


async def test_vote_requires_the_voting_state(service: SessionService) -> None:
    game_session = await service.start_session("user-1", "daily")
    current = await service.start_next_round(game_session.id, "user-1")
    with pytest.raises(ConflictError):  # still writing
        await service.vote(current.round_id, "user-1", "A")


async def test_vote_unknown_round(service: SessionService) -> None:
    with pytest.raises(NotFoundError):
        await service.vote("round-missing", "user-1", "A")


async def test_vote_twice_is_rejected(service: SessionService) -> None:
    game_session, current = await _start_round_with_entry(service)
    await service.vote(current.round_id, "user-1", "A")
    with pytest.raises(ConflictError):
        await service.vote(current.round_id, "user-1", "B")


# ---------------------------------------------------------------------------
# next_round + summary


async def _play_round(service: SessionService, game_session: models.Session) -> object:
    current = await service.start_next_round(game_session.id, "user-1")
    await service.submit_entry(current.round_id, VALID_ENTRY, "user-1")
    entries = await service.voting.present_entries(current.round_id)
    ai_letter = "B" if entries["A"] == VALID_ENTRY else "A"
    return await service.vote(current.round_id, "user-1", ai_letter)


async def test_next_round_advances_and_completes_the_session(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session = await service.start_session("user-1", "daily")
    earned = 0
    for expected_round in (1, 2, 3):
        current = await service.start_next_round(game_session.id, "user-1")
        assert current.round_number == expected_round
        result = await _play_round(service, game_session)
        earned += result.score.total

    # A fourth next_round completes the session instead of starting a round.
    assert await service.start_next_round(game_session.id, "user-1") is None
    updated = await db_session.get(models.Session, game_session.id)
    assert updated is not None and updated.completed_at is not None
    assert updated.final_score == earned  # sum of the three rounds' totals


async def test_session_summary_after_the_full_loop(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session = await service.start_session("user-1", "daily")
    earned = 0
    for _ in range(3):
        result = await _play_round(service, game_session)
        earned += result.score.total
    await service.start_next_round(game_session.id, "user-1")

    summary = await service.get_session_summary(game_session.id, "user-1")
    assert summary.session_id == game_session.id
    assert summary.total_score == earned
    assert summary.accuracy == 100.0
    assert summary.rounds_total == 3
    assert summary.rounds_played == 3
    assert len(summary.rounds) == 3
    assert summary.rounds[0].correct is True
    assert summary.rounds[0].score is not None
    assert summary.rounds[0].vote in ("A", "B")
    assert summary.streak == 3  # three correct guesses in a row


async def test_session_summary_mixed_accuracy(
    service: SessionService, db_session: AsyncSession
) -> None:
    game_session = await service.start_session("user-1", "daily")
    first = await _play_round(service, game_session)  # correct

    current = await service.start_next_round(game_session.id, "user-1")
    await service.submit_entry(current.round_id, VALID_ENTRY, "user-1")
    entries = await service.voting.present_entries(current.round_id)
    ai_letter = "B" if entries["A"] == VALID_ENTRY else "A"
    second = await service.vote(current.round_id, "user-1", "A" if ai_letter == "B" else "B")  # wrong

    summary = await service.get_session_summary(game_session.id, "user-1")
    assert summary.total_score == first.score.total + second.score.total
    assert summary.accuracy == 50.0
    assert summary.streak == 0


async def test_session_summary_unknown_session(service: SessionService) -> None:
    with pytest.raises(NotFoundError):
        await service.get_session_summary("session-missing", "user-1")


# ---------------------------------------------------------------------------
# HTTP game loop (start -> entry -> vote -> next -> summary)


def _api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "session_api.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    from app import main

    return main.app


def test_http_game_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The full 3-round game over REST, with the StubProvider (E2E contract)."""
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "stub_provider_only", True)
    monkeypatch.setattr(settings, "ollama_enabled", False)
    app = _api_client(tmp_path, monkeypatch)
    with TestClient(app) as client:
        guest = client.post("/api/v1/auth/guest", json={}).json()
        headers = {"Authorization": f"Bearer {guest['token']}"}

        started = client.post(
            "/api/v1/session/start", json={"type": "daily"}, headers=headers
        )
        assert started.status_code == 201, started.text
        session_id = started.json()["session_id"]
        round_id = started.json()["round_id"]
        assert round_id

        totals = []
        for expected in (1, 2, 3):
            entry = client.post(
                f"/api/v1/session/{session_id}/rounds/{round_id}/entry",
                json={"entry": VALID_ENTRY},
                headers=headers,
            )
            assert entry.status_code == 200, entry.text
            body = entry.json()
            assert set(body["entries"]) == {"A", "B"}
            assert VALID_ENTRY in body["entries"].values()

            ai_letter = "B" if body["entries"]["A"] == VALID_ENTRY else "A"
            voted = client.post(
                "/api/v1/voting/vote",
                json={"round_id": round_id, "vote": ai_letter},
                headers=headers,
            )
            assert voted.status_code == 200, voted.text
            assert voted.json()["vote_correct"] is True
            totals.append(voted.json()["total"])

            nxt = client.post(f"/api/v1/session/{session_id}/next", headers=headers)
            assert nxt.status_code == 200, nxt.text
            nxt_body = nxt.json()
            if expected < 3:
                assert nxt_body["complete"] is False
                assert nxt_body["round"]["round_number"] == expected + 1
                round_id = nxt_body["round"]["round_id"]
            else:
                assert nxt_body["complete"] is True

        summary = client.get(f"/api/v1/session/{session_id}/summary", headers=headers)
        assert summary.status_code == 200
        body = summary.json()
        assert body["total_score"] == sum(totals)
        assert body["accuracy"] == 100.0
        assert len(body["rounds"]) == 3
        assert body["streak"] == 3

        # The session reports itself complete now.
        state = client.get(f"/api/v1/session/{session_id}", headers=headers)
        assert state.json()["state"] == "completed"


def test_http_entry_submission_requires_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "stub_provider_only", True)
    app = _api_client(tmp_path, monkeypatch)
    with TestClient(app) as client:
        owner = client.post("/api/v1/auth/guest", json={}).json()
        stranger = client.post("/api/v1/auth/guest", json={}).json()
        started = client.post(
            "/api/v1/session/start",
            json={"type": "daily"},
            headers={"Authorization": f"Bearer {owner['token']}"},
        ).json()

        response = client.post(
            f"/api/v1/session/{started['session_id']}/rounds/{started['round_id']}/entry",
            json={"entry": VALID_ENTRY},
            headers={"Authorization": f"Bearer {stranger['token']}"},
        )
        assert response.status_code == 404  # foreign sessions are invisible


def test_http_entry_submission_maps_provider_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every provider in the chain failing surfaces as 503, not a crash."""
    from fastapi.testclient import TestClient

    from app.services.ai.providers import ProviderError
    from app.services.ai_service import AIService

    async def boom(self, challenge, retry_on_injection: int = 3) -> str:
        raise ProviderError("all providers down")

    monkeypatch.setattr(AIService, "generate_entry", boom)
    monkeypatch.setattr(settings, "stub_provider_only", True)
    app = _api_client(tmp_path, monkeypatch)
    with TestClient(app) as client:
        guest = client.post("/api/v1/auth/guest", json={}).json()
        headers = {"Authorization": f"Bearer {guest['token']}"}
        started = client.post(
            "/api/v1/session/start", json={"type": "daily"}, headers=headers
        ).json()

        response = client.post(
            f"/api/v1/session/{started['session_id']}/rounds/{started['round_id']}/entry",
            json={"entry": VALID_ENTRY},
            headers=headers,
        )
        assert response.status_code == 503
