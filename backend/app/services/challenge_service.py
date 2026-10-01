"""Challenge Engine: loads definitions, applies constraints, rotates daily challenges.

The JSON library is the source of truth (Master Architecture §12); it is loaded
into memory once per service instance. The database only records which
challenge was assigned to which date (`challenge_daily`).
"""

import json
import random
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.challenge import ChallengeRepository
from app.schemas.challenge import ChallengeDefinition, ConstraintResult, ValidationResult
from app.services.constraint_engine import ConstraintEngine
from app.services.input_validator import InputValidator
from app.services.scoring_engine import ScoringEngine

LIBRARY_DIR = Path(__file__).resolve().parents[1] / "data" / "challenge_library"

# Fixed seed so every process builds the identical rotation permutation.
_ROTATION_SEED = 20260928


class ChallengeService:
    def __init__(self, challenge_repo: ChallengeRepository) -> None:
        self.repo = challenge_repo
        self.constraint_engine = ConstraintEngine()
        self.input_validator = InputValidator()
        self.scoring_engine = ScoringEngine()
        self._library = self._load_library()
        pool = sorted(self._library)
        self._rotation_order = random.Random(_ROTATION_SEED).sample(pool, len(pool))

    @staticmethod
    def _load_library() -> dict[str, ChallengeDefinition]:
        library: dict[str, ChallengeDefinition] = {}
        for path in sorted(LIBRARY_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            definition = ChallengeDefinition.model_validate(data)
            library[definition.id] = definition
        return library

    def get_challenge(self, challenge_id: str) -> ChallengeDefinition:
        """Full definition for a challenge id (KeyError for unknown ids — a bug, not input)."""
        if challenge_id not in self._library:
            raise KeyError(f"unknown challenge: {challenge_id}")
        return self._library[challenge_id]

    def get_challenge_pool(self) -> list[str]:
        """All challenge IDs (for rotation)."""
        return sorted(self._library)

    def apply_constraints(self, entry: str, challenge: ChallengeDefinition) -> ConstraintResult:
        """Hard violations block submission; soft violations are tracked only."""
        return self.constraint_engine.validate(entry, challenge.constraints)

    def validate_input(self, entry: str | None, input_type: str) -> ValidationResult:
        return self.input_validator.validate(entry, input_type)

    def generate_time_limit(self, challenge: ChallengeDefinition, difficulty: int) -> int:
        """Base time adjusted by difficulty: harder -> less time (tension), clamped to schema bounds."""
        delta = challenge.difficulty - difficulty
        adjusted = challenge.time_limit_seconds + delta * 2
        return max(10, min(120, adjusted))

    def rotate_daily_challenge(self, for_date: date) -> ChallengeDefinition:
        """Deterministic daily pick: fixed permutation indexed by day, so a full cycle
        (len(pool) days) covers every challenge exactly once."""
        index = for_date.toordinal() % len(self._rotation_order)
        return self._library[self._rotation_order[index]]

    def get_daily_session_pool(self, for_date: date, rounds: int = 3) -> list[str]:
        """Challenge ids for a daily session: consecutive rotation entries starting at today's pick."""
        start = for_date.toordinal() % len(self._rotation_order)
        return [
            self._rotation_order[(start + offset) % len(self._rotation_order)]
            for offset in range(rounds)
        ]

    async def get_daily_challenge(
        self, for_date: date, player_rating: float | None = None
    ) -> ChallengeDefinition:
        """Today's challenge: reuse the persisted assignment, else rotate and persist.

        `player_rating` is reserved for adaptive difficulty (§12.3), not enabled in the MVP.
        """
        assigned = await self.repo.get_daily(for_date)
        if assigned is not None:
            return self.get_challenge(assigned.id)
        chosen = self.rotate_daily_challenge(for_date)
        await self.repo.increment_daily_usage(chosen.id, for_date=for_date)
        return chosen


async def sync_library_to_db(session: AsyncSession) -> int:
    """Idempotently insert the JSON library into the challenges table.

    The endpoints that write `challenge_daily` need the rows to satisfy the FK;
    Sprint 26 owns the full load script + data migration. Returns rows added.
    """
    from app.db.models import Challenge

    added = 0
    for path in sorted(LIBRARY_DIR.glob("*.json")):
        definition = ChallengeDefinition.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if await session.get(Challenge, definition.id) is not None:
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
        added += 1
    if added:
        await session.commit()
    return added
