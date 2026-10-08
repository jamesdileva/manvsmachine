"""Leaderboard schemas: entry rows and endpoint responses."""

import datetime as dt

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


class DailyLeaderboardResponse(BaseModel):
    """Today's (or a given date's) board: rows ranked by total score."""

    date: dt.date
    entries: list[LeaderboardEntry]


class AllTimeLeaderboardResponse(BaseModel):
    """All-time board: rows ranked by Detection Rating."""

    entries: list[LeaderboardEntry]
