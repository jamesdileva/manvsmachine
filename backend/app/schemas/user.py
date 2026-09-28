"""Auth and profile schemas."""

from pydantic import BaseModel, Field


class GuestAuthRequest(BaseModel):
    """Optional guest_id to resume an existing guest, else a new one is issued."""

    guest_id: str | None = None
    display_name: str | None = None


class RegisterRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=40)


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    guest_id: str | None = None
    display_name: str
    is_guest: bool = False
    token: str


class MeResponse(BaseModel):
    user_id: str
    guest_id: str | None = None
    display_name: str
    is_guest: bool = False
