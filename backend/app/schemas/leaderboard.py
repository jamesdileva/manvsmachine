"""Leaderboard entry shared schema."""

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    """A ranked leaderboard row.

    Daily boards fill `score`; the all-time board fills `rating`.
    `accuracy` is populated by the LeaderboardService (Sprint 12).
    """

    rank: int
    user_id: str
    display_name: str
    score: int | None = None
    rating: float | None = None
    accuracy: float | None = None
