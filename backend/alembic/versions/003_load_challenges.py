"""load challenge library

Revision ID: 003
Revises: 002
Create Date: 2026-10-10 00:00:00.000000

Data migration: inserts the 25 challenge definitions from
app/data/challenge_library into the challenges table. Idempotent — existing
ids are left alone, so a re-run is a no-op.
"""

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# app/data/challenge_library, relative to the backend root.
LIBRARY_DIR = Path(__file__).resolve().parents[2] / "app" / "data" / "challenge_library"

_CHALLENGES = sa.table(
    "challenges",
    sa.column("id", sa.String),
    sa.column("name", sa.String),
    sa.column("interaction_type", sa.String),
    sa.column("prompt", sa.String),
    sa.column("constraints", sa.JSON),
    sa.column("time_limit_seconds", sa.Integer),
    sa.column("input_type", sa.String),
    sa.column("voting_criteria", sa.String),
    sa.column("difficulty", sa.Integer),
    sa.column("scoring_rules", sa.JSON),
    sa.column("ai_prompt_template_id", sa.String),
    sa.column("replayability", sa.JSON),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    bind = op.get_bind()
    present = {
        row[0] for row in bind.execute(sa.text("SELECT id FROM challenges"))
    }

    for path in sorted(LIBRARY_DIR.glob("*.json")):
        definition = json.loads(path.read_text(encoding="utf-8"))
        if definition["id"] in present:
            continue
        constraints = [
            {key: value for key, value in constraint.items() if value is not None}
            for constraint in definition["constraints"]
        ]
        bind.execute(
            _CHALLENGES.insert().values(
                id=definition["id"],
                name=definition["name"],
                interaction_type=definition["interactionType"],
                prompt=definition["prompt"],
                constraints=json.dumps(constraints),
                time_limit_seconds=definition["timeLimitSeconds"],
                input_type=definition["inputType"],
                voting_criteria=definition["votingCriteria"],
                difficulty=definition["difficulty"],
                scoring_rules=json.dumps(definition["scoringRules"]),
                ai_prompt_template_id=definition["aiPromptTemplateId"],
                replayability=json.dumps(definition["replayability"]),
                created_at=sa.func.now(),
                updated_at=sa.func.now(),
            )
        )


def downgrade() -> None:
    for path in sorted(LIBRARY_DIR.glob("*.json")):
        definition = json.loads(path.read_text(encoding="utf-8"))
        op.execute(
            _CHALLENGES.delete().where(_CHALLENGES.c.id == definition["id"])
        )
