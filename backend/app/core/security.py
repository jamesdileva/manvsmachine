"""Security utilities: JWT issuing/validation and password hashing.

JWTs use PyJWT (HS256). Passwords use stdlib PBKDF2-HMAC-SHA256 with a random
salt — passlib is unmaintained and increasingly incompatible with modern
Python, and no hashing library is specified in the Master Architecture §8.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.exceptions import AuthenticationError

_PBKDF2_ITERATIONS = 240_000
bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: str) -> str:
    """Issue a signed access token for a user."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str:
    """Validate a token and return the user id it was issued for."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("invalid or expired token") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("invalid token payload")
    return str(user_id)


def hash_password(password: str) -> str:
    """Hash a password: pbkdf2_sha256$iterations$salt_hex$hash_hex."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time password check against a stored hash."""
    if not stored:
        return False
    try:
        algorithm, iterations, salt_hex, hash_hex = stored.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
    )
    return hmac.compare_digest(digest.hex(), hash_hex)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency: require a valid Bearer token, return the user id."""
    if credentials is None:
        raise AuthenticationError("missing bearer token")
    return decode_token(credentials.credentials)
