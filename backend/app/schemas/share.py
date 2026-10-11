"""Share endpoint schemas (Implementation Guide §2.6; backend from Sprint 25)."""

from pydantic import BaseModel, Field


class ShareRequest(BaseModel):
    """Generate a shareable result for a completed session."""

    session_id: str
    format: str = "image"  # "image" (default) or "text"
    message: str | None = None  # the player's own words, echoed onto the card


class ShareResponse(BaseModel):
    share_text: str
    share_url: str
    # Base64 PNG result card; None for the text-only format.
    share_image: str | None = None


class ShareReplayRound(BaseModel):
    """One round of the shared replay, with both entries attributed."""

    round_number: int
    challenge_id: str
    human_entry: str
    ai_entry: str
    vote: str | None = None
    correct: bool | None = None
    score: int | None = None
    humanity_human: int | None = None
    humanity_ai: int | None = None


class ShareReplaySummary(BaseModel):
    session_id: str
    type: str
    total_score: int
    accuracy: float | None = None
    rounds: list[ShareReplayRound] = Field(default_factory=list)


class ShareReplayResponse(BaseModel):
    """`GET /share/s/{session_id}`: what a shared link resolves to."""

    share_text: str
    share_url: str
    summary: ShareReplaySummary
