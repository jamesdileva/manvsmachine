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


class RecentHumanityScore(BaseModel):
    """One recent entry's humanity score, keyed by its challenge (Implementation Guide §2.5)."""

    challenge_id: str
    score: int
    date: str


class ProfileResponse(BaseModel):
    """`GET /profile` payload (Implementation Guide §2.5)."""

    user_id: str
    display_name: str
    is_guest: bool = False
    detection_rating: float
    total_rounds: int
    overall_accuracy: float
    current_streak: int
    longest_streak: int
    daily_challenge_streak: int
    recent_humanity_scores: list[RecentHumanityScore] = []


class ProfileUpdateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)
