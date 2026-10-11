"""Shared pytest fixtures (introduced with Sprint 24's E2E suite).

`client` runs the app against a throwaway SQLite file with the StubProvider
forced (Implementation Guide §12.4 step 1), so the E2E flow never needs real
AI API keys. Test files that define their own `client` fixture shadow this
one, so existing suites are unaffected.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """TestClient on a throwaway DB with the StubProvider forced."""
    db_file = tmp_path / "e2e.db"
    monkeypatch.setattr(
        settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}"
    )
    monkeypatch.setattr(settings, "stub_provider_only", True)
    monkeypatch.setattr(settings, "ollama_enabled", False)
    from app import main

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def expected_challenges() -> dict[str, dict]:
    """The practice challenge definitions, as pinned in tests/fixtures/challenges."""
    definitions = {}
    for path in sorted((FIXTURES_DIR / "challenges").glob("*.json")):
        definition = json.loads(path.read_text(encoding="utf-8"))
        definitions[definition["id"]] = definition
    return definitions


@pytest.fixture
def ai_responses() -> dict:
    """Sample AI responses + the sanitization contract they are checked against."""
    path = FIXTURES_DIR / "ai_responses" / "sanitization_samples.json"
    return json.loads(path.read_text(encoding="utf-8"))
