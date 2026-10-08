"""Voting endpoints: entry submission + AI generation trigger (Sprint 10, partial).

The round/entry persistence and vote endpoint land in Sprints 11-13; this
endpoint validates the human entry and produces the AI entry for the round.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.security import get_current_user_id
from app.db.connection import get_session
from app.repositories.challenge import ChallengeRepository
from app.repositories.prompt_audit import PromptAuditRepository
from app.schemas.voting import SubmitEntryRequest, SubmitEntryResponse
from app.services.ai.providers import ProviderError
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.content_filter import ContentFilter
from app.services.prompt_audit_service import PromptAuditService

router = APIRouter(prefix="/voting", tags=["voting"])


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
