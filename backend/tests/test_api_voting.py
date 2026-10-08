"""Voting endpoint tests (Sprint 10) — entry submission + AI generation trigger."""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlmodel import select

from app.core.config import settings
from app.db import models  # noqa: F401 — registers tables on SQLModel.metadata
from app.db.connection import make_engine

CHALLENGE_ID = "challenge_slogan_01"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_file = tmp_path / "api.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    from app import main

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def stub_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the StubProvider: no real AI calls, no API keys needed (E2E contract)."""
    monkeypatch.setattr(settings, "stub_provider_only", True)
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "ollama_enabled", False)


def _auth_headers(client: TestClient) -> dict[str, str]:
    body = client.post("/api/v1/auth/guest", json={}).json()
    return {"Authorization": f"Bearer {body['token']}"}


def _audit_rows(db_file: Path) -> list[models.PromptAudit]:
    async def fetch() -> list[models.PromptAudit]:
        engine: AsyncEngine = make_engine(f"sqlite+aiosqlite:///{db_file.as_posix()}")
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            rows = (await session.execute(select(models.PromptAudit))).scalars().all()
        await engine.dispose()
        return list(rows)

    return asyncio.run(fetch())


# ---------------------------------------------------------------------------
# POST /voting/submit-entry


def test_submit_entry_returns_both_entries(
    client: TestClient, tmp_path: Path, stub_only: None
) -> None:
    response = client.post(
        "/api/v1/voting/submit-entry",
        json={"challenge_id": CHALLENGE_ID, "entry": "Fire baked. Dragon approved."},
        headers=_auth_headers(client),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["challenge_id"] == CHALLENGE_ID
    assert body["human_entry"] == "Fire baked. Dragon approved."
    assert body["ai_entry"]
    assert body["provider"] == "stub"
    assert body["model"] == "stub-v1"
    assert body["hard_violations"] == []
    assert body["soft_violations"] == []


def test_submit_entry_reports_soft_violations(client: TestClient, stub_only: None) -> None:
    # challenge_tweet_09's must_include_theme ("plant") constraint is soft.
    response = client.post(
        "/api/v1/voting/submit-entry",
        json={
            "challenge_id": "challenge_tweet_09",
            "entry": "i keep forgetting to water things oops",
        },
        headers=_auth_headers(client),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["hard_violations"] == []
    assert any("plant" in violation for violation in body["soft_violations"])


def test_submit_entry_blocks_hard_violations(client: TestClient, stub_only: None) -> None:
    response = client.post(
        "/api/v1/voting/submit-entry",
        json={
            "challenge_id": CHALLENGE_ID,
            "entry": "Fresh bread from the dragons own oven, baked daily",
        },
        headers=_auth_headers(client),
    )
    assert response.status_code == 400
    violations = response.json()["detail"]["hard_violations"]
    assert any("too many words" in violation for violation in violations)


def test_submit_entry_unknown_challenge(client: TestClient, stub_only: None) -> None:
    response = client.post(
        "/api/v1/voting/submit-entry",
        json={"challenge_id": "challenge_missing_99", "entry": "anything"},
        headers=_auth_headers(client),
    )
    assert response.status_code == 404


def test_submit_entry_rejects_empty_entry(client: TestClient, stub_only: None) -> None:
    response = client.post(
        "/api/v1/voting/submit-entry",
        json={"challenge_id": CHALLENGE_ID, "entry": "   "},
        headers=_auth_headers(client),
    )
    assert response.status_code == 400


def test_submit_entry_maps_provider_failure_to_503(
    client: TestClient, stub_only: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.ai.providers import ProviderError
    from app.services.ai_service import AIService

    async def boom(self: AIService, challenge, retry_on_injection: int = 3) -> str:
        raise ProviderError("all providers down")

    monkeypatch.setattr(AIService, "generate_entry", boom)
    response = client.post(
        "/api/v1/voting/submit-entry",
        json={"challenge_id": CHALLENGE_ID, "entry": "Fire baked. Dragon approved."},
        headers=_auth_headers(client),
    )
    assert response.status_code == 503


def test_submit_entry_requires_auth(client: TestClient, stub_only: None) -> None:
    response = client.post(
        "/api/v1/voting/submit-entry",
        json={"challenge_id": CHALLENGE_ID, "entry": "Fire baked. Dragon approved."},
    )
    assert response.status_code == 401


def test_submit_entry_records_audit(
    client: TestClient, tmp_path: Path, stub_only: None
) -> None:
    response = client.post(
        "/api/v1/voting/submit-entry",
        json={"challenge_id": CHALLENGE_ID, "entry": "Fire baked. Dragon approved."},
        headers=_auth_headers(client),
    )
    assert response.status_code == 200

    rows = _audit_rows(tmp_path / "api.db")
    assert len(rows) == 1
    assert rows[0].challenge_id == CHALLENGE_ID
    assert rows[0].provider == "stub"
    assert rows[0].ai_response == response.json()["ai_entry"]
