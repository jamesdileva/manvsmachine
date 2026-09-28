"""Custom application exceptions mapped to HTTP responses in main.py."""

from typing import Any


class AppError(Exception):
    """Base class for errors that map to a JSON HTTP response."""

    status_code: int = 500

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class AuthenticationError(AppError):
    """Invalid or missing credentials."""

    status_code = 401


class NotFoundError(AppError):
    """Requested resource does not exist."""

    status_code = 404


class ConflictError(AppError):
    """Resource already exists / state conflict."""

    status_code = 409


def error_detail(exc: AppError) -> dict[str, Any]:
    """FastAPI-style JSON error body."""
    return {"detail": str(exc)}
