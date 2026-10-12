"""Challenge library database load + daily rotation tests (Sprint 26).

Covers the sprint's acceptance criteria at the database level: all 25
definitions load, `/challenges/daily` picks one of them deterministically,
`/challenges/{id}` serves any of them in full, and the rotation never
repeats inside a 25-day cycle.
"""

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import delete, func, select

from app.core.config import settings
from app.db import models
from app.db.connection import make_engine, run_migrations
from app.scripts.challenge_data import library_ids, load_challenge_library
from app.services.challenge_service import ChallengeService

BACKEND_DIR = Path(__file__).resolve().parents[1]
LIBRARY_IDS = library_ids()
TODAY = dt.date(2026, 10, 10)


@pytest.fixture
async def empty_db(tmp_path: Path) -> str:
    """A migrated database with NO challenges loaded yet (for the load tests).

    Migration 003 already inserts the library, so it is cleared here to make the
    loader's first run a genuine load rather than a no-op.
    """
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'challenges.db').as_posix()}"
    run_migrations(db_url)
    await _clear_challenges(db_url)
    return db_url


@pytest.fixture
async def loaded_db(empty_db: str) -> str:
    """The migrated database with the challenge library loaded (for rotation/endpoints)."""
    assert await _load(empty_db) == 25  # the rotation's FK needs the challenge rows
    return empty_db


@pytest.fixture
def client(loaded_db: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", loaded_db)
    monkeypatch.setattr(settings, "stub_provider_only", True)
    from app import main

    with TestClient(main.app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# The load: all 25 definitions reach the database


async def test_load_challenge_library_inserts_every_definition(empty_db: str) -> None:
    assert await _load(empty_db) == 25
    assert await _challenge_count(empty_db) == 25


async def test_load_challenge_library_is_idempotent(empty_db: str) -> None:
    assert await _load(empty_db) == 25
    assert await _load(empty_db) == 0
    assert await _challenge_count(empty_db) == 25


async def test_loaded_definitions_match_the_json_files(empty_db: str) -> None:
    from app.schemas.challenge import ChallengeDefinition

    await _load(empty_db)
    rows = {row.id: row for row in await _all_challenges(empty_db)}
    assert set(rows) == LIBRARY_IDS

    for challenge_id in LIBRARY_IDS:
        definition = ChallengeDefinition.model_validate_json(
            (BACKEND_DIR / "app" / "data" / "challenge_library" / f"{challenge_id}.json").read_text(
                encoding="utf-8"
            )
        )
        row = rows[challenge_id]
        dumped = definition.model_dump(by_alias=True)
        assert row.name == definition.name
        assert row.prompt == definition.prompt
        assert row.time_limit_seconds == definition.time_limit_seconds
        assert row.difficulty == definition.difficulty
        # The JSON column round-trips as plain dicts; compare the same shape.
        assert row.constraints == dumped["constraints"]
        assert row.scoring_rules == dumped["scoringRules"]


async def test_load_fills_every_column_of_the_challenge_row(empty_db: str) -> None:
    await _load(empty_db)
    row = (await _all_challenges(empty_db))[0]

    assert row.interaction_type
    assert row.input_type
    assert row.voting_criteria
    assert row.ai_prompt_template_id == "v1.0"
    assert row.replayability
    assert row.created_at is not None


# ---------------------------------------------------------------------------
# The daily rotation


async def test_rotation_persists_one_assignment_per_date(loaded_db: str) -> None:
    """`challenge_daily` gets exactly one row per date, and repeats reuse it."""
    from app.repositories.challenge import ChallengeRepository

    async with _session(loaded_db) as session:
        service = ChallengeService(ChallengeRepository(session))

        first = await service.get_daily_challenge(TODAY)
        again = await service.get_daily_challenge(TODAY)

        assert first.id == again.id
        rows = (await session.execute(select(models.ChallengeDaily))).scalars().all()
        assert len(rows) == 1
        assert rows[0].challenge_id == first.id


async def test_rotation_never_repeats_within_a_25_day_cycle(loaded_db: str) -> None:
    """Acceptance criterion: 25 consecutive days cover all 25 challenges once."""
    from app.repositories.challenge import ChallengeRepository

    async with _session(loaded_db) as session:
        service = ChallengeService(ChallengeRepository(session))
        picked = [
            (await service.get_daily_challenge(TODAY + dt.timedelta(days=offset))).id
            for offset in range(25)
        ]

    assert set(picked) == LIBRARY_IDS
    assert len(picked) == 25


async def test_rotation_is_deterministic_across_services(loaded_db: str) -> None:
    """A fresh service (new process, same seed) picks the same challenge for a date."""
    from app.repositories.challenge import ChallengeRepository

    async with _session(loaded_db) as session:
        first = await ChallengeService(ChallengeRepository(session)).get_daily_challenge(TODAY)

    async with _session(loaded_db) as session:
        second = await ChallengeService(ChallengeRepository(session)).get_daily_challenge(
            TODAY + dt.timedelta(days=25)  # a full cycle later: back to the same pick
        )

    assert first.id == second.id


# ---------------------------------------------------------------------------
# HTTP endpoints over the loaded library


def _token(client: TestClient) -> str:
    return client.post("/api/v1/auth/guest", json={}).json()["token"]


def test_daily_returns_one_of_the_loaded_challenges(client: TestClient) -> None:
    response = client.get(
        "/api/v1/challenges/daily",
        headers={"Authorization": f"Bearer {_token(client)}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["challenge"]["id"] in LIBRARY_IDS


def test_every_challenge_is_served_by_id(client: TestClient) -> None:
    for challenge_id in LIBRARY_IDS:
        response = client.get(f"/api/v1/challenges/{challenge_id}")
        assert response.status_code == 200, response.text
        # The endpoint returns the definition itself (not wrapped).
        definition = response.json()
        assert definition["id"] == challenge_id
        assert definition["prompt"].strip()
        assert definition["timeLimitSeconds"] >= 10


def test_unknown_challenge_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/challenges/challenge_nope_99").status_code == 404


# ---------------------------------------------------------------------------
# Helpers


async def _load(db_url: str) -> int:
    async with _session(db_url) as session:
        return await load_challenge_library(session)


async def _clear_challenges(db_url: str) -> None:
    """Empty the challenges table (migration 003 pre-populates it)."""
    async with _session(db_url) as session:
        await session.execute(delete(models.Challenge))
        await session.commit()


def _session(db_url: str):
    """A session on the throwaway database (caller closes via the context manager)."""
    engine = make_engine(db_url)
    return async_sessionmaker(engine, expire_on_commit=False)()


async def _challenge_count(db_url: str) -> int:
    async with _session(db_url) as session:
        count = (
            await session.execute(select(func.count(models.Challenge.id)))
        ).scalar_one()
        return int(count)


async def _all_challenges(db_url: str) -> list[models.Challenge]:
    async with _session(db_url) as session:
        return list((await session.execute(select(models.Challenge))).scalars().all())

