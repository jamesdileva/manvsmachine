"""Voting schemas: entry submission (Sprint 10); vote payloads arrive in Sprint 11."""

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
