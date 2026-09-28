"""Auth endpoint, security, and state store tests (Sprint 4)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient against a throwaway DB, lifespan included."""
    db_file = tmp_path / "auth.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    from app import main

    with TestClient(main.app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Password hashing (stdlib PBKDF2)


def test_password_hashing() -> None:
    from app.core.security import hash_password, verify_password

    stored = hash_password("correct horse battery staple")
    assert stored != "correct horse battery staple"
    assert verify_password("correct horse battery staple", stored)
    assert not verify_password("wrong password", stored)
    assert not verify_password("anything", None)
    assert not verify_password("anything", "garbage")


# ---------------------------------------------------------------------------
# JWT tokens


def test_token_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.exceptions import AuthenticationError
    from app.core.security import create_access_token, decode_token

    token = create_access_token("user-123")
    assert decode_token(token) == "user-123"

    monkeypatch.setattr(settings, "jwt_expire_minutes", -1)  # already expired
    expired = create_access_token("user-123")
    with pytest.raises(AuthenticationError):
        decode_token(expired)

    with pytest.raises(AuthenticationError):
        decode_token("not-a-jwt")


# ---------------------------------------------------------------------------
# State store


def test_state_store() -> None:
    from app.core.state import StateStore

    store = StateStore()
    assert store.get("round-1") is None
    store.set("round-1", {"state": "voting"})
    assert store.get("round-1") == {"state": "voting"}
    store.delete("round-1")
    assert store.get("round-1") is None
    store.set("a", {})
    store.set("b", {})
    store.clear()
    assert store.get("a") is None and store.get("b") is None


# ---------------------------------------------------------------------------
# Auth endpoints


def test_guest_endpoint(client: TestClient) -> None:
    from app.core.security import decode_token

    response = client.post("/api/v1/auth/guest", json={})
    assert response.status_code == 201
    body = response.json()
    assert body["is_guest"] is True
    assert body["guest_id"] and body["user_id"] and body["display_name"]
    assert decode_token(body["token"]) == body["user_id"]
    assert body["display_name"].startswith("Player_")


def test_guest_get_or_create(client: TestClient) -> None:
    first = client.post("/api/v1/auth/guest", json={}).json()
    again = client.post("/api/v1/auth/guest", json={"guest_id": first["guest_id"]}).json()
    assert again["user_id"] == first["user_id"]
    assert again["display_name"] == first["display_name"]


def test_register_and_login(client: TestClient) -> None:
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "alex@example.com", "password": "s3cure-pass", "display_name": "Alex"},
    )
    assert register.status_code == 201
    body = register.json()
    assert body["is_guest"] is False and body["guest_id"] is None

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "alex@example.com", "password": "s3cure-pass", "display_name": "Alex"},
    )
    assert duplicate.status_code == 409

    short_password = client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "short", "display_name": "O"},
    )
    assert short_password.status_code == 422

    login = client.post("/api/v1/auth/login", json={"email": "alex@example.com", "password": "s3cure-pass"})
    assert login.status_code == 200
    assert login.json()["user_id"] == body["user_id"]

    wrong_password = client.post("/api/v1/auth/login", json={"email": "alex@example.com", "password": "nope-nope"})
    assert wrong_password.status_code == 401
    unknown_email = client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "s3cure-pass"})
    assert unknown_email.status_code == 401


def test_me_requires_valid_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    )

    register = client.post(
        "/api/v1/auth/register",
        json={"email": "sam@example.com", "password": "s3cure-pass", "display_name": "Sam"},
    ).json()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {register['token']}"})
    assert me.status_code == 200
    assert me.json()["user_id"] == register["user_id"]
    assert me.json()["display_name"] == "Sam"
    assert me.json()["is_guest"] is False
