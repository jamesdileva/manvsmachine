"""Challenge and session API endpoint tests (Sprint 7)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_file = tmp_path / "api.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    from app import main

    with TestClient(main.app) as test_client:
        yield test_client


def _auth_headers(client: TestClient) -> dict[str, str]:
    body = client.post("/api/v1/auth/guest", json={}).json()
    return {"Authorization": f"Bearer {body['token']}"}


# ---------------------------------------------------------------------------
# Challenge endpoints


def test_get_challenge_definition_public(client: TestClient) -> None:
    response = client.get("/api/v1/challenges/challenge_slogan_01")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "challenge_slogan_01"
    assert body["name"] == "Tiny Tagline"
    assert body["timeLimitSeconds"] == 15  # full definition uses the file's camelCase shape
    assert body["constraints"][0]["isHard"] is True
    assert body["aiPromptGuidance"]

    assert client.get("/api/v1/challenges/challenge_missing_99").status_code == 404


def test_validate_endpoint(client: TestClient) -> None:
    valid = client.post(
        "/api/v1/challenges/validate",
        json={"challenge_id": "challenge_slogan_01", "entry": "Fire baked. Dragon approved."},
    )
    assert valid.status_code == 200
    body = valid.json()
    assert body["valid"] is True
    assert body["hard_violations"] == []
    assert body["word_count"] == 4  # "Fire baked. Dragon approved." — the doc's example mislabels it 5
    assert body["character_count"] == len("Fire baked. Dragon approved.")

    too_long = client.post(
        "/api/v1/challenges/validate",
        json={"challenge_id": "challenge_slogan_01", "entry": "one two three four five six"},
    )
    body = too_long.json()
    assert body["valid"] is False
    assert body["hard_violations"] and body["word_count"] == 6

    unknown = client.post(
        "/api/v1/challenges/validate",
        json={"challenge_id": "challenge_missing_99", "entry": "hi"},
    )
    assert unknown.status_code == 404


def test_daily_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/challenges/daily").status_code == 401


def test_daily_creates_and_reuses_daily_session(client: TestClient) -> None:
    headers = _auth_headers(client)

    first = client.get("/api/v1/challenges/daily", headers=headers)
    assert first.status_code == 200
    body = first.json()
    assert body["round_number"] == 1
    assert body["challenge"]["id"].startswith("challenge_")
    assert body["challenge"]["constraints"][0]["isHard"] in (True, False)
    assert body["challenge"]["time_limit_seconds"] >= 10
    assert body["session_id"]

    # Second call reuses the active daily session and today's assignment.
    second = client.get("/api/v1/challenges/daily", headers=headers).json()
    assert second["session_id"] == body["session_id"]
    assert second["challenge"]["id"] == body["challenge"]["id"]

    # The daily session's challenge pool starts with today's pick.
    state = client.get(f"/api/v1/session/{body['session_id']}", headers=headers).json()
    assert state["type"] == "daily" and state["rounds_total"] == 3


# ---------------------------------------------------------------------------
# Session endpoints


def test_session_start_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/session/start", json={"type": "daily"}).status_code == 401


def test_session_start_daily(client: TestClient) -> None:
    headers = _auth_headers(client)

    started = client.post("/api/v1/session/start", json={"type": "daily"}, headers=headers)
    assert started.status_code == 201
    body = started.json()
    assert body["type"] == "daily" and body["rounds_total"] == 3
    assert body["next_challenge"]["id"].startswith("challenge_")
    assert body["next_challenge"]["prompt"]
    assert body["next_challenge"]["time_limit_seconds"] >= 10

    state = client.get(f"/api/v1/session/{body['session_id']}", headers=headers)
    assert state.status_code == 200
    state_body = state.json()
    assert state_body["current_round"] == 1
    assert state_body["state"] == "in_progress"
    assert state_body["started_at"]

    assert client.get("/api/v1/session/missing-session", headers=headers).status_code == 404


def test_session_start_practice(client: TestClient) -> None:
    headers = _auth_headers(client)

    explicit = client.post(
        "/api/v1/session/start",
        json={
            "type": "practice",
            "challenge_ids": ["challenge_slogan_01", "challenge_emoji_03", "challenge_movie_10"],
        },
        headers=headers,
    )
    assert explicit.status_code == 201
    assert explicit.json()["next_challenge"]["id"] == "challenge_slogan_01"
    assert explicit.json()["type"] == "practice"

    unknown = client.post(
        "/api/v1/session/start",
        json={"type": "practice", "challenge_ids": ["challenge_missing_99"]},
        headers=headers,
    )
    assert unknown.status_code == 404

    random_pick = client.post("/api/v1/session/start", json={"type": "practice"}, headers=headers)
    assert random_pick.status_code == 201
    assert random_pick.json()["rounds_total"] == 3

    invalid_type = client.post("/api/v1/session/start", json={"type": "ranked"}, headers=headers)
    assert invalid_type.status_code == 422


def test_session_ownership_enforced(client: TestClient) -> None:
    owner = _auth_headers(client)
    stranger = _auth_headers(client)

    session_id = client.post("/api/v1/session/start", json={"type": "daily"}, headers=owner).json()[
        "session_id"
    ]
    assert client.get(f"/api/v1/session/{session_id}", headers=stranger).status_code == 404
    assert (
        client.get(f"/api/v1/session/{session_id}/summary", headers=stranger).status_code == 404
    )


def test_session_summary(client: TestClient) -> None:
    headers = _auth_headers(client)
    session_id = client.post("/api/v1/session/start", json={"type": "daily"}, headers=headers).json()[
        "session_id"
    ]

    summary = client.get(f"/api/v1/session/{session_id}/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["session_id"] == session_id
    assert body["total_score"] == 0  # no rounds played yet
    assert body["accuracy"] is None  # populated by scoring service (Sprint 12/13)
    assert body["rounds"] == []
    assert client.get("/api/v1/session/missing-session/summary", headers=headers).status_code == 404
