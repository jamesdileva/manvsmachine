"""Session and daily-challenge response schemas (Implementation Guide §2.2/§2.3)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.challenge import ChallengeOut
from app.schemas.scoring import RoundScore
from app.schemas.voting import RevealResult


class SessionStartRequest(BaseModel):
    type: Literal["daily", "practice"] = "daily"
    challenge_ids: list[str] | None = None


class RoundEntryRequest(BaseModel):
    """A human entry submitted for a specific round of a session."""

    entry: str


class ChallengeBrief(BaseModel):
    id: str
    prompt: str
    time_limit_seconds: int


class SessionStartResponse(BaseModel):
    session_id: str
    type: str
    rounds_total: int
    next_challenge: ChallengeBrief
    round_id: str | None = None  # the first round's id (Sprint 13)


class SessionStateResponse(BaseModel):
    session_id: str
    type: str
    current_round: int
    rounds_total: int
    state: str
    started_at: datetime
    completed_at: datetime | None = None


class RoundSummary(BaseModel):
    """Per-round summary; correctness/score/humanity fill in from Sprint 12/13 onward."""

    round_number: int
    challenge_id: str
    vote: str | None = None
    correct: bool | None = None
    score: int | None = None
    humanity_human: int | None = None
    humanity_ai: int | None = None


class SessionSummaryResponse(BaseModel):
    session_id: str
    type: str
    total_score: int
    accuracy: float | None = None
    rounds: list[RoundSummary] = Field(default_factory=list)
    rating_change: float | None = None
    streak: int | None = None


class DailyChallengeResponse(BaseModel):
    challenge: ChallengeOut
    session_id: str
    round_number: int
    round_id: str | None = None  # the current round's id (Sprint 13)


# ---------------------------------------------------------------------------
# Service DTOs (Sprint 13: the SessionService's round lifecycle)


class RoundState(BaseModel):
    """The round a player is about to play."""

    round_id: str
    challenge: ChallengeBrief
    round_number: int
    rounds_total: int
    state: str


class RoundSubmission(BaseModel):
    """Both entries for a round, anonymized as A/B (no attribution)."""

    round_id: str
    entries: dict[str, str] = Field(default_factory=dict)
    ai_provider: str = ""
    ai_model: str = ""
    hard_violations: list[str] = Field(default_factory=list)
    soft_violations: list[str] = Field(default_factory=list)


class RoundResult(BaseModel):
    """Vote outcome: the reveal plus the round's score and rating effects."""

    round_id: str
    reveal: RevealResult
    score: RoundScore
    rating: float
    rating_change: float = 0.0
    streak: int


class NextRoundResponse(BaseModel):
    """Either the next round to play or the completed session."""

    complete: bool = False
    round: RoundState | None = None


class SessionSummary(BaseModel):
    """Session totals computed from the rounds and scores (service DTO)."""

    session_id: str
    type: str
    rounds_total: int
    rounds_played: int
    total_score: int
    accuracy: float | None = None
    rounds: list[RoundSummary] = Field(default_factory=list)
    rating_change: float | None = None  # needs a session-start rating snapshot (not in the MVP schema)
    streak: int | None = None


class SessionOverview(BaseModel):
    """Session shape for the SESSION_STARTED handshake (service DTO)."""

    session_id: str
    type: str
    rounds_total: int
    rounds_played: int
    completed: bool = False
    challenges: list[ChallengeBrief] = Field(default_factory=list)
