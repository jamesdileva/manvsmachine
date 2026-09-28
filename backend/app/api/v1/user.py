"""Auth and user endpoints (guest sessions, register, login, profile)."""

import secrets
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from app.db.connection import get_session
from app.db.models import User
from app.repositories.user import UserRepository
from app.schemas.user import (
    AuthResponse,
    GuestAuthRequest,
    LoginRequest,
    MeResponse,
    RegisterRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _generate_guest_name() -> str:
    return f"Player_{secrets.randbelow(9000) + 1000}"


@router.post("/guest", response_model=AuthResponse, status_code=201)
async def create_guest_session(
    body: GuestAuthRequest, session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    """Create a guest session, or resume one when guest_id is provided."""
    repo = UserRepository(session)
    user = await repo.get_by_guest_id(body.guest_id) if body.guest_id else None
    if user is None:
        display_name = body.display_name or _generate_guest_name()
        guest_id = body.guest_id or str(uuid.uuid4())
        user = await repo.create_guest(display_name, guest_id=guest_id)
    return AuthResponse(
        user_id=user.id,
        guest_id=user.guest_id,
        display_name=user.display_name,
        is_guest=True,
        token=create_access_token(user.id),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    """Create a named account with email + password."""
    existing = (
        await session.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("email already registered")
    repo = UserRepository(session)
    user = User(
        display_name=body.display_name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    await repo.create(user)
    return AuthResponse(
        user_id=user.id,
        display_name=user.display_name,
        is_guest=False,
        token=create_access_token(user.id),
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    """Exchange email + password for an access token."""
    user = (
        await session.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise AuthenticationError("invalid email or password")
    return AuthResponse(
        user_id=user.id,
        display_name=user.display_name,
        is_guest=False,
        token=create_access_token(user.id),
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    """Profile for the token holder (protected)."""
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise NotFoundError("user not found")
    return MeResponse(
        user_id=user.id,
        guest_id=user.guest_id,
        display_name=user.display_name,
        is_guest=user.password_hash is None,
    )
