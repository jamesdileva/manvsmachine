"""Voting schemas: entry submission (Sprint 10); votes and reveals (Sprint 11)."""

from pydantic import BaseModel, Field


class SubmitEntryRequest(BaseModel):
    """A human entry submitted for the active challenge."""

    challenge_id: str
    entry: str


class SubmitEntryResponse(BaseModel):
    """The human entry plus the generated (sanitized) AI entry."""

    challenge_id: str
    human_entry: str
    ai_entry: str
    provider: str
    model: str
    hard_violations: list[str] = Field(default_factory=list)
    soft_violations: list[str] = Field(default_factory=list)


class VoteRequest(BaseModel):
    """Which anonymized entry (A/B) the player believes is the AI's."""

    round_id: str
    vote: str


class VoteResult(BaseModel):
    """Outcome of recording a vote: can the round proceed to reveal?"""

    round_id: str
    vote: str
    can_reveal: bool
    total_votes: int


class RevealResult(BaseModel):
    """The round's attribution, humanity scores, and explanation."""

    round_id: str
    entries: dict[str, str] = Field(default_factory=dict)
    human_was: str
    ai_was: str
    vote: str | None = None
    vote_correct: bool
    humanity_human: float
    humanity_ai: float
    explanation: str
