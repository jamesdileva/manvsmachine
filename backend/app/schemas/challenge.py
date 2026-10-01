"""Challenge definition schemas.

Parse the camelCase challenge JSON (Implementation Guide §10.1) via aliases and
expose snake_case attributes internally; the API layer (Sprint 7) serializes
snake_case per the endpoint contracts.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConstraintType = Literal[
    "max_words",
    "max_characters",
    "must_rhyme",
    "no_adjectives",
    "must_include_theme",
    "exactly_n_emojis",
    "no_letter_e",
    "one_sentence_only",
]


class Constraint(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: ConstraintType
    value: int | str | None = None
    is_hard: bool = Field(default=True, alias="isHard")
    description: str | None = None


class ScoringRules(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    base_score: int = Field(default=100, alias="baseScore")
    time_bonus_multiplier: float = Field(default=0.1, alias="timeBonusMultiplier")
    streak_multiplier: float = Field(default=0.05, alias="streakMultiplier")


class Replayability(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    daily_variants: int = Field(default=1, alias="dailyVariants")
    constraint_pool: list[str] = Field(default_factory=list, alias="constraintPool")


class ChallengeDefinition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    interaction_type: str = Field(default="Quick Text", alias="interactionType")
    prompt: str
    constraints: list[Constraint] = Field(default_factory=list)
    time_limit_seconds: int = Field(default=20, alias="timeLimitSeconds")
    input_type: str = Field(default="text_single_line", alias="inputType")
    voting_criteria: str = Field(default="most_believable", alias="votingCriteria")
    difficulty: int = 2
    scoring_rules: ScoringRules = Field(default_factory=ScoringRules, alias="scoringRules")
    ai_prompt_template_id: str = Field(alias="aiPromptTemplateId")
    ai_prompt_guidance: str = Field(default="", alias="aiPromptGuidance")
    replayability: Replayability = Field(default_factory=Replayability, alias="replayability")


class ConstraintResult(BaseModel):
    """Outcome of validating an entry against a challenge's constraints."""

    valid: bool
    hard_violations: list[str] = Field(default_factory=list)
    soft_violations: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Outcome of input-type validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API response shapes (contracts per Implementation Guide §2.2)


class ConstraintOut(BaseModel):
    """Constraint as exposed by the API — keeps the file format's camelCase `isHard`."""

    model_config = ConfigDict(populate_by_name=True)

    type: ConstraintType
    value: int | str | None = None
    is_hard: bool = Field(default=True, alias="isHard")


class ChallengeOut(BaseModel):
    """Challenge brief for the daily endpoint (snake_case, per §2.2's example)."""

    id: str
    name: str
    prompt: str
    constraints: list[ConstraintOut] = Field(default_factory=list)
    time_limit_seconds: int
    input_type: str
    voting_criteria: str
    difficulty: int

    @classmethod
    def from_definition(cls, definition: ChallengeDefinition) -> "ChallengeOut":
        return cls(
            id=definition.id,
            name=definition.name,
            prompt=definition.prompt,
            constraints=[
                ConstraintOut.model_validate({"type": c.type, "value": c.value, "isHard": c.is_hard})
                for c in definition.constraints
            ],
            time_limit_seconds=definition.time_limit_seconds,
            input_type=definition.input_type,
            voting_criteria=definition.voting_criteria,
            difficulty=definition.difficulty,
        )


class ValidateRequest(BaseModel):
    challenge_id: str
    entry: str


class ValidateResponse(BaseModel):
    valid: bool
    hard_violations: list[str] = Field(default_factory=list)
    soft_violations: list[str] = Field(default_factory=list)
    word_count: int
    character_count: int
