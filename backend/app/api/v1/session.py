"""Session endpoints: start, state, summary, round advance (Sprint 13 orchestration)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.security import get_current_user_id
from app.db.connection import get_session
from app.repositories.challenge import ChallengeRepository
from app.repositories.prompt_audit import PromptAuditRepository
from app.repositories.scoring import ScoringRepository
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.repositories.voting import VotingRepository
from app.schemas.session import (
    NextRoundResponse,
    RoundEntryRequest,
    RoundSubmission,
    SessionStartRequest,
    SessionStartResponse,
    SessionStateResponse,
    SessionSummaryResponse,
)
from app.services.ai.providers import ProviderError
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.content_filter import ContentFilter
from app.services.prompt_audit_service import PromptAuditService
from app.services.scoring_service import ScoringService
from app.services.session_service import SessionService
from app.services.voting_service import VotingService

router = APIRouter(prefix="/session", tags=["session"])


def _session_service(session: AsyncSession) -> SessionService:
    """Request-scoped SessionService wired to this request's DB session."""
    return SessionService(
        SessionRepository(session),
        ChallengeService(ChallengeRepository(session)),
        AIService(
            settings,
            ContentFilter(),
            PromptAuditService(PromptAuditRepository(session)),
        ),
        VotingService(VotingRepository(session)),
        ScoringService(ScoringRepository(session), UserRepository(session)),
    )


@router.post("/start", response_model=SessionStartResponse, status_code=201)
async def start_session(
    body: SessionStartRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> SessionStartResponse:
    """Start a session: daily uses today's 3-rotation pool; practice uses explicit or random ids."""
    service = _session_service(session)
    game_session = await service.start_session(user_id, body.type, body.challenge_ids)
    current = await service.start_next_round(game_session.id, user_id)
    assert current is not None  # a fresh session always has its first round
    return SessionStartResponse(
        session_id=game_session.id,
        type=body.type,
        rounds_total=len(game_session.challenge_ids),
        next_challenge=current.challenge,
        round_id=current.round_id,
    )


async def _get_owned_session(session_id: str, user_id: str, session: AsyncSession):
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
    """Session totals + accuracy + per-round breakdown, computed from the rounds."""
    await _get_owned_session(session_id, user_id, session)
    summary = await _session_service(session).get_session_summary(session_id, user_id)
    return SessionSummaryResponse(
        session_id=summary.session_id,
        type=summary.type,
        total_score=summary.total_score,
        accuracy=summary.accuracy,
        rounds=summary.rounds,
        rating_change=summary.rating_change,
        streak=summary.streak,
    )


@router.post("/{session_id}/next", response_model=NextRoundResponse)
async def next_round(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> NextRoundResponse:
    """Advance to the next round; reports completion once every round is played."""
    await _get_owned_session(session_id, user_id, session)
    current = await _session_service(session).start_next_round(session_id, user_id)
    if current is None:
        return NextRoundResponse(complete=True)
    return NextRoundResponse(complete=False, round=current)


@router.post("/{session_id}/rounds/{round_id}/entry", response_model=RoundSubmission)
async def submit_round_entry(
    session_id: str,
    round_id: str,
    body: RoundEntryRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> RoundSubmission:
    """Submit the human entry for a round; returns both entries anonymized as A/B."""
    await _get_owned_session(session_id, user_id, session)
    try:
        return await _session_service(session).submit_entry(round_id, body.entry, user_id)
    except ProviderError as exc:  # every provider in the chain failed
        raise HTTPException(status_code=503, detail=str(exc)) from exc
