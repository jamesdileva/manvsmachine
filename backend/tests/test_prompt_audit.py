"""PromptAuditService tests (Sprint 8) — template loading, versioning, audit trail."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings
from app.db import models  # noqa: F401 — registers tables on SQLModel.metadata
from app.db.connection import make_engine
from app.repositories.prompt_audit import PromptAuditRepository


@pytest.fixture
def tmp_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / 'audit_test.db').as_posix()}"


@pytest.fixture
async def db_session(tmp_db_url: str) -> AsyncSession:
    engine: AsyncEngine = make_engine(tmp_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def service(db_session: AsyncSession):
    from app.services.prompt_audit_service import PromptAuditService

    return PromptAuditService(PromptAuditRepository(db_session))


async def _seed_challenge(session: AsyncSession, challenge_id: str = "challenge_slogan_01") -> None:
    session.add(
        models.Challenge(
            id=challenge_id,
            name="Tiny Tagline",
            prompt="Write a slogan for a dragon-owned bakery.",
            ai_prompt_template_id="v1.0",
        )
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Template loading


def test_get_prompt_template_loads_v1_0(service) -> None:  # type: ignore[no-untyped-def]
    template = service.get_prompt_template("v1.0")
    assert template.version == "v1.0"
    assert template.system_prompt.startswith("You are a creative assistant")
    assert "{prompt}" in template.user_template
    assert template.instructions
    assert template.humanity_guidance


def test_get_prompt_template_unknown_version_raises(service) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(KeyError):
        service.get_prompt_template("v9.9")


def test_get_active_version_matches_settings(service) -> None:  # type: ignore[no-untyped-def]
    assert service.get_active_version() == settings.ai_prompt_version


def test_list_versions_returns_template_files(service) -> None:  # type: ignore[no-untyped-def]
    assert service.list_versions() == ["v1.0"]


# ---------------------------------------------------------------------------
# Audit recording


async def test_record_usage_stores_prompt_and_response(service, db_session: AsyncSession) -> None:
    await _seed_challenge(db_session)
    row = await service.record_usage(
        challenge_id="challenge_slogan_01",
        prompt="Challenge: Write a slogan for a dragon-owned bakery.\n\nYour entry:",
        response="Fire baked. Dragon approved.",
        provider="stub",
        model="stub-v1",
    )
    assert row.id
    assert row.prompt_version == "v1.0"
    assert row.prompt_system.startswith("You are a creative assistant")
    assert row.prompt_user == "Challenge: Write a slogan for a dragon-owned bakery.\n\nYour entry:"
    assert row.ai_response == "Fire baked. Dragon approved."
    assert row.raw_response == "Fire baked. Dragon approved."
    assert row.provider == "stub"
    assert row.model == "stub-v1"
    assert row.token_count is None

    stored = await service.repo.get_by_challenge("challenge_slogan_01")
    assert [entry.id for entry in stored] == [row.id]
    assert await service.repo.get_versions() == ["v1.0"]


async def test_record_usage_keeps_raw_response_separate(service, db_session: AsyncSession) -> None:
    await _seed_challenge(db_session)
    row = await service.record_usage(
        challenge_id="challenge_slogan_01",
        prompt="Challenge: ...",
        response="I think this bakery is divine.",
        provider="openai",
        model="gpt-4o-mini",
        token_count=42,
        raw_response="As an AI, I think this bakery is divine.",
    )
    assert row.ai_response == "I think this bakery is divine."
    assert row.raw_response == "As an AI, I think this bakery is divine."
    assert row.token_count == 42
    assert row.provider == "openai"
    assert row.model == "gpt-4o-mini"


async def test_record_usage_honours_explicit_version(service, db_session: AsyncSession) -> None:
    await _seed_challenge(db_session)
    row = await service.record_usage(
        challenge_id="challenge_slogan_01",
        prompt="Challenge: ...",
        response="Fire baked.",
        provider="stub",
        model="stub-v1",
        prompt_version="v1.0",
    )
    assert row.prompt_version == "v1.0"
    assert row.prompt_system == service.get_prompt_template("v1.0").system_prompt


async def test_record_usage_unknown_version_raises(service, db_session: AsyncSession) -> None:
    await _seed_challenge(db_session)
    with pytest.raises(KeyError):
        await service.record_usage(
            challenge_id="challenge_slogan_01",
            prompt="Challenge: ...",
            response="Fire baked.",
            provider="stub",
            model="stub-v1",
            prompt_version="v9.9",
        )
