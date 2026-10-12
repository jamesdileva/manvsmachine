"""Load the challenge library into the database.

Usage (from the project root, with the project venv active):

    python scripts/load_challenges.py

The JSON files in backend/app/data/challenge_library are the source of truth
(AGENTS.md core rule 1: challenges are data, not code). This script inserts any
missing definitions and is idempotent — safe to re-run at any time. The app's
startup does the same sync, so this exists for explicit/timed loads and for
verifying what is in the database.
"""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.connection import run_migrations  # noqa: E402
from app.scripts.challenge_data import (  # noqa: E402
    library_ids,
    load_challenge_library,
)
from app.db.connection import make_engine  # noqa: E402
from app.core.config import settings  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlmodel import func, select  # noqa: E402

from app.db.models import Challenge  # noqa: E402


async def _load() -> tuple[int, int]:
    """Migrate if needed, then load; returns (rows added, rows now present)."""
    run_migrations(settings.database_url)
    engine = make_engine(settings.database_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        added = await load_challenge_library(
            session,
            on_progress=lambda index, total, definition: print(
                f"  [{index:>2}/{len(library_ids())}] {definition.id}"
            ),
        )
        count = int(
            (await session.execute(select(func.count(Challenge.id)))).scalar_one()
        )
    await engine.dispose()
    return added, count


def main() -> int:
    print(f"loading challenge library from {BACKEND_DIR / 'app' / 'data' / 'challenge_library'}")
    added, count = asyncio.run(_load())
    if added:
        print(f"loaded {added} challenge(s) into the database ({count} present)")
    else:
        print(f"nothing to do — all {count} challenge(s) already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
