"""Session endpoints: start, state, summary."""

import random

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.exceptions import NotFoundError
from app.core.security import get_current_user_id
from app.db.connection import get_session
from app.db.models import Round, utc_now
from app.repositories.challenge import ChallengeRepository
from app.repositories.session import SessionRepository
from app.schemas.session import (
    ChallengeBrief,
    RoundSummary,
    SessionStartRequest,
    SessionStartResponse,
    SessionStateResponse,
    SessionSummaryResponse,
)
from app.services.challenge_service import ChallengeService

router = APIRouter(prefix="/session", tags=["session"])

SESSION_ROUNDS = 3


@router.post("/start", response_model=SessionStartResponse, status_code=201)
async def start_session(
    body: SessionStartRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> SessionStartResponse:
    """Start a session: daily uses today's 3-rotation pool; practice uses explicit or random ids."""
    service = ChallengeService(ChallengeRepository(session))
    if body.type == "daily":
        challenge_ids = service.get_daily_session_pool(utc_now().date())
    elif body.challenge_ids:
        challenge_ids = body.challenge_ids[:SESSION_ROUNDS]
        for challenge_id in challenge_ids:
            try:
                service.get_challenge(challenge_id)
            except KeyError as exc:
                raise NotFoundError(f"unknown challenge: {challenge_id}") from exc
    else:
        challenge_ids = random.sample(service.get_challenge_pool(), SESSION_ROUNDS)

    game_session = await SessionRepository(session).create(
        user_id, challenge_ids, is_daily=body.type == "daily"
    )
    first = service.get_challenge(challenge_ids[0])
    return SessionStartResponse(
        session_id=game_session.id,
        type=body.type,
        rounds_total=len(challenge_ids),
        next_challenge=ChallengeBrief(
            id=first.id,
            prompt=first.prompt,
            time_limit_seconds=first.time_limit_seconds,
        ),
    )


async def _get_owned_session(
    session_id: str, user_id: str, session: AsyncSession
):
    """Fetch a session owned by the user; unknown or foreign sessions both 404."""
    game_session = await SessionRepository(session).get(session_id)
    if game_session is None or game_session.user_id != user_id:
        raise NotFoundError("session not found")
    return game_session


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session_state(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> SessionStateResponse:
    game_session = await _get_owned_session(session_id, user_id, session)
    return SessionStateResponse(
        session_id=game_session.id,
        type="daily" if game_session.is_daily else "practice",
        current_round=min(game_session.rounds_played + 1, len(game_session.challenge_ids)),
        rounds_total=len(game_session.challenge_ids),
        state="completed" if game_session.completed_at else "in_progress",
        started_at=game_session.started_at,
        completed_at=game_session.completed_at,
    )


@router.get("/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> SessionSummaryResponse:
    game_session = await _get_owned_session(session_id, user_id, session)
    rounds = (
        await session.execute(
            select(Round)
            .where(Round.session_id == game_session.id)
            .order_by(col(Round.round_number))
        )
    ).scalars().all()
    return SessionSummaryResponse(
        session_id=game_session.id,
        type="daily" if game_session.is_daily else "practice",
        total_score=game_session.final_score or 0,
        accuracy=None,  # computed by the scoring service (Sprint 12/13)
        rounds=[
            RoundSummary(
                round_number=round_row.round_number,
                challenge_id=round_row.challenge_id,
                vote=round_row.vote,
                humanity_human=round_row.reveal_data.get("humanity_human"),
                humanity_ai=round_row.reveal_data.get("humanity_ai"),
            )
            for round_row in rounds
        ],
        rating_change=None,
        streak=None,
    )
