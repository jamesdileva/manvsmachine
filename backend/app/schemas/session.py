"""Session and daily-challenge response schemas (Implementation Guide §2.2/§2.3)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.challenge import ChallengeOut


class SessionStartRequest(BaseModel):
    type: Literal["daily", "practice"] = "daily"
    challenge_ids: list[str] | None = None


class ChallengeBrief(BaseModel):
    id: str
    prompt: str
    time_limit_seconds: int


class SessionStartResponse(BaseModel):
    session_id: str
    type: str
    rounds_total: int
    next_challenge: ChallengeBrief


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
