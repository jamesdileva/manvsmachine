"""Share endpoints: result cards and replay links (Implementation Guide §2.6)."""

import base64

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.security import get_current_user_id
from app.db.connection import get_session
from app.db.models import Entry
from app.repositories.challenge import ChallengeRepository
from app.repositories.prompt_audit import PromptAuditRepository
from app.repositories.scoring import ScoringRepository
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.repositories.voting import VotingRepository
from app.schemas.session import SessionSummary
from app.schemas.share import (
    ShareReplayResponse,
    ShareReplayRound,
    ShareReplaySummary,
    ShareRequest,
    ShareResponse,
)
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.content_filter import ContentFilter
from app.services.prompt_audit_service import PromptAuditService
from app.services.scoring_service import ScoringService
from app.services.session_service import SessionService
from app.services.share_service import ShareService
from app.services.voting_service import VotingService

router = APIRouter(prefix="/share", tags=["share"])


@router.post("/result", response_model=ShareResponse)
async def create_share_result(
    body: ShareRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ShareResponse:
    """Text (+ PNG card) for a finished session the caller owns."""
    game_session = await SessionRepository(session).get(body.session_id)
    if game_session is None or game_session.user_id != user_id:
        raise NotFoundError("session not found")
    if game_session.completed_at is None:
        raise HTTPException(status_code=400, detail="session is not finished yet")

    summary = await _summary_for(session, body.session_id, user_id)
    service = ShareService()
    image = (
        None
        if body.format == "text"
        else base64.b64encode(service.generate_share_image(summary)).decode("ascii")
    )
    return ShareResponse(
        share_text=service.generate_share_text(summary),
        share_url=service.create_share_link(body.session_id),
        share_image=image,
    )


@router.get("/s/{session_id}", response_model=ShareReplayResponse)
async def get_share_replay(
    session_id: str,
    _viewer: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ShareReplayResponse:
    """Resolve a shared link: the result text plus the attributed rounds.

    The link exists to be shown to other players, so the replay reads through
    the session owner's identity rather than the viewer's.
    """
    sessions = SessionRepository(session)
    game_session = await sessions.get(session_id)
    if game_session is None:
        raise NotFoundError("share not found")

    summary = await _summary_for(session, session_id, game_session.user_id)
    rounds = await sessions.get_rounds_for_session(session_id)
    entries = {rnd.round_number: rnd for rnd in rounds}

    service = ShareService()
    return ShareReplayResponse(
        share_text=service.generate_share_text(summary),
        share_url=service.create_share_link(session_id),
        summary=ShareReplaySummary(
            session_id=summary.session_id,
            type=summary.type,
            total_score=summary.total_score,
            accuracy=summary.accuracy,
            rounds=[
                ShareReplayRound(
                    round_number=entry.round_number,
                    challenge_id=entry.challenge_id,
                    human_entry=await _entry_text(session, rnd.human_entry_id if rnd else None),
                    ai_entry=await _entry_text(session, rnd.ai_entry_id if rnd else None),
                    vote=entry.vote,
                    correct=entry.correct,
                    score=entry.score,
                    humanity_human=entry.humanity_human,
                    humanity_ai=entry.humanity_ai,
                )
                for entry, rnd in (
                    (entry, entries.get(entry.round_number)) for entry in summary.rounds
                )
            ],
        ),
    )


async def _summary_for(
    session: AsyncSession, session_id: str, user_id: str
) -> SessionSummary:
    """The session summary, read on behalf of the user who owns it."""
    return await _session_service(session).get_session_summary(session_id, user_id)


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


async def _entry_text(session: AsyncSession, entry_id: str | None) -> str:
    if not entry_id:
        return ""
    entry = await session.get(Entry, entry_id)
    return entry.content if entry else ""
