"""Database schema, connection, and migration tests (Sprint 2)."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel

from app.core.config import settings

EXPECTED_TABLES = {
    "users",
    "challenges",
    "challenge_daily",
    "sessions",
    "rounds",
    "entries",
    "ai_entries",
    "votes",
    "scores",
    "humanity_scores",
    "streaks",
    "leaderboard_snapshots",
    "prompt_audit",
}

EXPECTED_INDEXES = {
    "idx_users_guest_id",
    "idx_users_detection_rating",
    "idx_sessions_user_id",
    "idx_sessions_started_at",
    "idx_rounds_session_id",
    "idx_rounds_challenge_id",
    "idx_rounds_state",
    "idx_entries_round_id",
    "idx_entries_author_type",
    "idx_votes_round_id",
    "idx_votes_user_id",
    "idx_scores_user_id",
    "idx_scores_scored_at",
    "idx_humanity_scores_last_updated",
    "idx_streaks_user_type",
    "idx_leaderboard_date",
    "idx_prompt_audit_recorded_at",
    "idx_prompt_audit_challenge_id",
}


@pytest.fixture
def tmp_db_url(tmp_path: Path) -> str:
    """SQLite URL for a throwaway database file."""
    return f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"


async def _table_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        return {row[0] for row in rows}


async def _index_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        )
        return {row[0] for row in rows}


async def test_create_all_creates_expected_tables(tmp_db_url: str) -> None:
    from app.db import models  # noqa: F401 — registers tables on SQLModel.metadata
    from app.db.connection import make_engine

    engine = make_engine(tmp_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    try:
        assert EXPECTED_TABLES <= await _table_names(engine)
    finally:
        await engine.dispose()


async def test_create_all_creates_expected_indexes(tmp_db_url: str) -> None:
    from app.db import models  # noqa: F401
    from app.db.connection import make_engine

    engine = make_engine(tmp_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    try:
        assert EXPECTED_INDEXES <= await _index_names(engine)
    finally:
        await engine.dispose()


async def test_engine_enables_foreign_keys_and_wal(tmp_db_url: str) -> None:
    from app.db.connection import make_engine

    engine = make_engine(tmp_db_url)
    async with engine.connect() as conn:
        foreign_keys = (await conn.execute(text("PRAGMA foreign_keys"))).scalar()
        journal_mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
    await engine.dispose()
    assert foreign_keys == 1
    assert str(journal_mode).lower() == "wal"


def test_alembic_upgrade_creates_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "alembic.db"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    from app.db import models  # noqa: F401
    from app.db.connection import run_migrations

    run_migrations()

    con = sqlite3.connect(db_file)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        indexes = {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
        }
    finally:
        con.close()
    assert EXPECTED_TABLES <= tables
    assert EXPECTED_INDEXES <= indexes


def test_alembic_upgrade_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'i.db').as_posix()}")
    from app.db import models  # noqa: F401
    from app.db.connection import run_migrations

    run_migrations()
    run_migrations()  # second run must be a no-op, not an error


def test_app_startup_initializes_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_file = tmp_path / "app.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    from app import main

    with TestClient(main.app):
        pass  # lifespan startup ran init_db; shutdown ran close_db

    con = sqlite3.connect(db_file)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    assert EXPECTED_TABLES <= tables
