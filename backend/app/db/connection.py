"""Async SQLite connection management (aiosqlite + SQLAlchemy 2.0).

Owns the persistent store only — ephemeral WebSocket/round state is in-process
(`app/core/state.py`, Sprint 4). The engine is created lazily from current
settings so tests can point it at a throwaway database file.
"""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from starlette.concurrency import run_in_threadpool

from alembic import command
from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[2]

_engine: AsyncEngine | None = None


def _set_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
    """Enable foreign keys and WAL on every new DBAPI connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def make_engine(database_url: str | None = None) -> AsyncEngine:
    """Create an async engine for the given URL (default: configured DATABASE_URL)."""
    engine = create_async_engine(database_url or settings.database_url, echo=False)
    event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
    return engine


def get_engine() -> AsyncEngine:
    """Shared engine, built from current settings on first use."""
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yield an async session bound to the shared engine."""
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        yield session


def run_migrations(database_url: str | None = None) -> None:
    """Run Alembic migrations to head (blocking; wrap in a thread from async code).

    The URL resolution order lives in `alembic/env.py`: explicit argument here,
    then the ALEMBIC_DATABASE_URL environment variable, then app settings.
    """
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")


async def init_db(database_url: str | None = None) -> None:
    """Bring the database schema up to head. Called on FastAPI startup."""
    await run_in_threadpool(run_migrations, database_url)


async def close_db() -> None:
    """Dispose the shared engine. Called on FastAPI shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
