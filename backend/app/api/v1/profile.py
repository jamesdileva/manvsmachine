"""Profile endpoints: player stats and display-name updates (Implementation Guide §2.5)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.connection import get_session
from app.repositories.scoring import ScoringRepository
from app.repositories.user import UserRepository
from app.schemas.user import ProfileResponse, ProfileUpdateRequest
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


def _service(session: AsyncSession) -> ProfileService:
    return ProfileService(ScoringRepository(session), UserRepository(session))


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    """The token holder's profile: rating, rounds, accuracy, streaks, humanity."""
    return await _service(session).get_profile(user_id)


@router.put("", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    """Update the display name; returns the refreshed profile."""
    return await _service(session).update_display_name(user_id, body.display_name)
