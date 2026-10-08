"""Voting endpoints: entry submission + AI generation trigger (Sprint 10), vote + reveal + score (Sprint 11/13).

`/submit-entry` is the stateless practice path (validate + generate, no round).
The session-scoped round flow lives in `api/v1/session.py` (entry submission via
SessionService) and `/vote` below (SessionService.vote: reveal + score).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.core.security import get_current_user_id
from app.db.connection import get_session
from app.repositories.challenge import ChallengeRepository
from app.repositories.prompt_audit import PromptAuditRepository
from app.repositories.scoring import ScoringRepository
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.repositories.voting import VotingRepository
from app.schemas.voting import (
    SubmitEntryRequest,
    SubmitEntryResponse,
    VoteRequest,
    VoteResponse,
)
from app.services.ai.providers import ProviderError
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.content_filter import ContentFilter
from app.services.prompt_audit_service import PromptAuditService
from app.services.scoring_service import ScoringService
from app.services.session_service import SessionService
from app.services.voting_service import VotingService

router = APIRouter(prefix="/voting", tags=["voting"])


def _session_service(session: AsyncSession) -> SessionService:
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


@router.post("/submit-entry", response_model=SubmitEntryResponse)
async def submit_entry(
    body: SubmitEntryRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> SubmitEntryResponse:
    """Validate the human entry (hard violations block) and generate the AI entry."""
    challenges = ChallengeService(ChallengeRepository(session))
    try:
        challenge = challenges.get_challenge(body.challenge_id)
    except KeyError as exc:
        raise NotFoundError(f"unknown challenge: {body.challenge_id}") from exc

    input_result = challenges.validate_input(body.entry, challenge.input_type)
    if not input_result.valid:
        raise HTTPException(status_code=400, detail={"hard_violations": input_result.errors})

    constraints = challenges.apply_constraints(body.entry, challenge)
    if not constraints.valid:
        raise HTTPException(
            status_code=400, detail={"hard_violations": constraints.hard_violations}
        )

    ai_service = AIService(
        settings, ContentFilter(), PromptAuditService(PromptAuditRepository(session))
    )
    try:
        ai_entry = await ai_service.generate_entry(challenge)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await ai_service.aclose()

    provider = ai_service.active_provider
    return SubmitEntryResponse(
        challenge_id=challenge.id,
        human_entry=body.entry,
        ai_entry=ai_entry,
        provider=provider.get_provider_name() if provider else "unknown",
        model=provider.get_model_name() if provider else "unknown",
        hard_violations=constraints.hard_violations,
        soft_violations=constraints.soft_violations,
    )


@router.post("/vote", response_model=VoteResponse)
async def submit_vote(
    body: VoteRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> VoteResponse:
    """Record the player's vote (A/B = which entry is the AI); reveals and scores the round."""
    try:
        result = await _session_service(session).vote(body.round_id, user_id, body.vote)
    except AppError:
        raise
    except ValueError as exc:  # invalid vote letter
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    reveal = result.reveal
    return VoteResponse(
        round_id=reveal.round_id,
        entries=reveal.entries,
        human_was=reveal.human_was,
        ai_was=reveal.ai_was,
        vote=reveal.vote,
        vote_correct=reveal.vote_correct,
        humanity_human=reveal.humanity_human,
        humanity_ai=reveal.humanity_ai,
        explanation=reveal.explanation,
        base=result.score.base,
        time_bonus=result.score.time_bonus,
        streak_bonus=result.score.streak_bonus,
        total=result.score.total,
        detection_rating=result.rating,
        streak=result.streak,
    )
