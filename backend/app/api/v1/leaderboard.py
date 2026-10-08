"""Leaderboard endpoints: daily and all-time boards (Implementation Guide §2.4).

Public read-only aggregates (no auth — the guide's §2.4 does not require it, and
the future hosted deployment shows these boards to everyone).
"""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_session
from app.db.models import utc_now
from app.repositories.scoring import ScoringRepository
from app.repositories.user import UserRepository
from app.schemas.leaderboard import AllTimeLeaderboardResponse, DailyLeaderboardResponse
from app.services.leaderboard_service import LeaderboardService

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/daily", response_model=DailyLeaderboardResponse)
async def get_daily_leaderboard(
    date: str | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> DailyLeaderboardResponse:
    """Today's leaderboard (or ?date=YYYY-MM-DD for a past day)."""
    service = LeaderboardService(ScoringRepository(session), UserRepository(session))
    for_date = _parse_date(date)
    return await service.get_daily_leaderboard_response(for_date, limit)


@router.get("/all-time", response_model=AllTimeLeaderboardResponse)
async def get_all_time_leaderboard(
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> AllTimeLeaderboardResponse:
    """All-time leaderboard ranked by Detection Rating."""
    service = LeaderboardService(ScoringRepository(session), UserRepository(session))
    return AllTimeLeaderboardResponse(entries=await service.get_all_time_leaderboard(limit))


def _parse_date(date: str | None) -> dt.date:
    if not date:
        return utc_now().date()
    try:
        return dt.date.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid date: {date!r}") from exc
