"""Challenge endpoints: daily challenge, definitions, entry validation."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import get_current_user_id
from app.db.connection import get_session
from app.db.models import utc_now
from app.repositories.challenge import ChallengeRepository
from app.repositories.session import SessionRepository
from app.schemas.challenge import (
    ChallengeDefinition,
    ChallengeOut,
    ValidateRequest,
    ValidateResponse,
)
from app.schemas.session import DailyChallengeResponse
from app.services.challenge_service import ChallengeService

router = APIRouter(prefix="/challenges", tags=["challenges"])


@router.get("/daily", response_model=DailyChallengeResponse)
async def get_daily_challenge(
    player_rating: float | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> DailyChallengeResponse:
    """Today's challenge for the token holder; creates/reuses their daily session."""
    service = ChallengeService(ChallengeRepository(session))
    today = utc_now().date()
    challenge = await service.get_daily_challenge(today, player_rating)

    session_repo = SessionRepository(session)
    game_session = await session_repo.get_active_daily_session(user_id, today)
    if game_session is None:
        game_session = await session_repo.create(
            user_id, service.get_daily_session_pool(today), is_daily=True
        )
        # First round of the fresh session so the client has a round to play.
        await SessionRepository(session).create_round(
            game_session.id, game_session.challenge_ids[0], 1
        )

    round_number, round_id = await _current_round(session, game_session)
    return DailyChallengeResponse(
        challenge=ChallengeOut.from_definition(challenge),
        session_id=game_session.id,
        round_number=round_number,
        round_id=round_id,
    )


async def _current_round(session: AsyncSession, game_session) -> tuple[int, str]:
    """(round_number, round_id) of the session's current round, creating it if needed."""
    repo = SessionRepository(session)
    rounds = await repo.get_rounds_for_session(game_session.id)
    next_number = min(game_session.rounds_played + 1, len(game_session.challenge_ids))
    rnd = next((r for r in rounds if r.round_number == next_number), None)
    if rnd is None:
        rnd = await repo.create_round(
            game_session.id, game_session.challenge_ids[next_number - 1], next_number
        )
    return rnd.round_number, rnd.id


@router.post("/validate", response_model=ValidateResponse)
async def validate_entry(
    body: ValidateRequest, session: AsyncSession = Depends(get_session)
) -> ValidateResponse:
    """Soft-check an entry against a challenge's constraints (pre-submission hint)."""
    service = ChallengeService(ChallengeRepository(session))
    try:
        challenge = service.get_challenge(body.challenge_id)
    except KeyError as exc:
        raise NotFoundError(f"unknown challenge: {body.challenge_id}") from exc

    result = service.apply_constraints(body.entry, challenge)
    return ValidateResponse(
        valid=result.valid,
        hard_violations=result.hard_violations,
        soft_violations=result.soft_violations,
        word_count=len(body.entry.split()),
        character_count=len(body.entry),
    )


@router.get("/{challenge_id}", response_model=ChallengeDefinition)
async def get_challenge(
    challenge_id: str, session: AsyncSession = Depends(get_session)
) -> ChallengeDefinition:
    """Full challenge definition in the file's camelCase shape."""
    service = ChallengeService(ChallengeRepository(session))
    try:
        return service.get_challenge(challenge_id)
    except KeyError as exc:
        raise NotFoundError(f"unknown challenge: {challenge_id}") from exc
