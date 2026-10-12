"""Challenge library loading: the JSON files are the source of truth (Sprint 26).

`load_challenge_library` is the single path used by the data migration, the
standalone load script, and the app's startup sync — so all three agree on
what "loaded" means. Challenges are data, not code (AGENTS.md core rule 1).
"""

import json
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models import Challenge
from app.schemas.challenge import ChallengeDefinition

LIBRARY_DIR = Path(__file__).resolve().parents[1] / "data" / "challenge_library"

ProgressFn = Callable[[int, int, ChallengeDefinition], None]


def library_ids() -> set[str]:
    """Every challenge id in the library (from the file names)."""
    return {path.stem for path in LIBRARY_DIR.glob("*.json")}


def read_definitions() -> list[ChallengeDefinition]:
    """Every challenge definition from disk, sorted by id (deterministic order)."""
    return [
        ChallengeDefinition.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(LIBRARY_DIR.glob("*.json"))
    ]


async def load_challenge_library(
    session: AsyncSession,
    on_progress: ProgressFn | None = None,
) -> int:
    """Insert any missing challenge definitions; returns the rows added.

    Idempotent: existing ids are left untouched, so re-running is safe and the
    count reports what actually changed.
    """
    ids = sorted(library_ids())
    # Select on a mapped column needs the same ignore the scoring repository uses
    # for its aggregate selects.
    existing = set(
        (
            await session.execute(
                select(Challenge.id).where(Challenge.id.in_(ids))  # type: ignore[attr-defined]
            )
        ).scalars()
    )

    added = 0
    for index, definition in enumerate(read_definitions(), start=1):
        if definition.id in existing:
            continue
        dumped = definition.model_dump(by_alias=True)
        session.add(
            Challenge(
                id=definition.id,
                name=definition.name,
                interaction_type=definition.interaction_type,
                prompt=definition.prompt,
                constraints=dumped["constraints"],
                time_limit_seconds=definition.time_limit_seconds,
                input_type=definition.input_type,
                voting_criteria=definition.voting_criteria,
                difficulty=definition.difficulty,
                scoring_rules=dumped["scoringRules"],
                ai_prompt_template_id=definition.ai_prompt_template_id,
                replayability=dumped["replayability"],
            )
        )
        if on_progress:
            on_progress(index, len(existing) + added + 1, definition)
        added += 1

    if added:
        await session.commit()
    return added

