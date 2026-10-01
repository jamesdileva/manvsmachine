"""Challenge engine, constraint engine, scoring, and rotation tests (Sprint 6)."""

import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel

from app.db import models  # noqa: F401 — registers tables on SQLModel.metadata
from app.db.connection import make_engine
from app.repositories.challenge import ChallengeRepository
from app.schemas.challenge import ChallengeDefinition


@pytest.fixture
def tmp_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / 'engine_test.db').as_posix()}"


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
    from app.services.challenge_service import ChallengeService

    return ChallengeService(ChallengeRepository(db_session))


def make_challenge(**overrides: object) -> ChallengeDefinition:
    data: dict[str, object] = {
        "id": "challenge_test_01",
        "name": "Test Challenge",
        "prompt": "Do a thing.",
        "ai_prompt_template_id": "v1.0",
    }
    data.update(overrides)
    return ChallengeDefinition.model_validate(data)


# ---------------------------------------------------------------------------
# ChallengeService


def test_service_loads_full_challenge_definition(service) -> None:  # type: ignore[no-untyped-def]
    challenge = service.get_challenge("challenge_slogan_01")
    assert challenge.name == "Tiny Tagline"
    assert challenge.prompt == "Write a slogan for a dragon-owned bakery."
    assert challenge.time_limit_seconds == 15
    assert challenge.constraints[0].type == "max_words"
    assert challenge.constraints[0].is_hard is True
    assert challenge.constraints[0].value == 5
    assert challenge.ai_prompt_guidance
    assert challenge.scoring_rules.base_score == 100

    with pytest.raises(KeyError):
        service.get_challenge("challenge_missing_99")


def test_service_pool_contains_the_whole_library(service) -> None:  # type: ignore[no-untyped-def]
    pool = service.get_challenge_pool()
    assert len(pool) == 25
    assert "challenge_slogan_01" in pool
    assert pool == sorted(pool)


def test_rotation_is_deterministic_and_full_cycle(service) -> None:  # type: ignore[no-untyped-def]
    day = dt.date(2026, 9, 28)
    assert service.rotate_daily_challenge(day).id == service.rotate_daily_challenge(day).id

    # A full cycle covers every challenge exactly once (Sprint 26 criterion, verified early).
    picks = [service.rotate_daily_challenge(day + dt.timedelta(days=i)).id for i in range(25)]
    assert len(set(picks)) == 25


async def test_get_daily_challenge_persists_assignment(service, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    day = dt.date(2026, 9, 28)
    expected = service.rotate_daily_challenge(day)
    # Mirror Sprint 26's loaded DB: challenge_daily has an FK to challenges.
    db_session.add(
        models.Challenge(
            id=expected.id,
            name=expected.name,
            prompt=expected.prompt,
            ai_prompt_template_id=expected.ai_prompt_template_id,
        )
    )
    await db_session.commit()

    first = await service.get_daily_challenge(day)
    assert first.id == expected.id

    stored = await service.repo.get_daily(day)
    assert stored is not None and stored.id == first.id

    # Second call goes through the persisted assignment and must agree.
    second = await service.get_daily_challenge(day)
    assert second.id == first.id


def test_generate_time_limit_adjusts_and_clamps(service) -> None:  # type: ignore[no-untyped-def]
    challenge = service.get_challenge("challenge_slogan_01")  # difficulty 2, 15s base

    assert service.generate_time_limit(challenge, 2) == 15  # unchanged at base difficulty
    assert service.generate_time_limit(challenge, 4) == 11  # harder -> less time
    assert service.generate_time_limit(challenge, 1) == 17  # easier -> more time
    assert service.generate_time_limit(challenge, 50) == 10  # clamped to schema minimum


# ---------------------------------------------------------------------------
# ConstraintEngine


@pytest.fixture
def engine():
    from app.services.constraint_engine import ConstraintEngine

    return ConstraintEngine()


def test_max_words(engine) -> None:  # type: ignore[no-untyped-def]
    from app.schemas.challenge import Constraint

    result = engine.validate("one two three four five six", [Constraint(type="max_words", value=5, is_hard=True)])
    assert result.valid is False
    assert result.hard_violations and "6" in result.hard_violations[0]

    ok = engine.validate("one two three four five", [Constraint(type="max_words", value=5, is_hard=True)])
    assert ok.valid is True and ok.hard_violations == []


def test_max_characters(engine) -> None:  # type: ignore[no-untyped-def]
    from app.schemas.challenge import Constraint

    result = engine.validate("12345678901", [Constraint(type="max_characters", value=10, is_hard=True)])
    assert result.valid is False and result.hard_violations


def test_must_include_theme_hard_and_soft(engine) -> None:  # type: ignore[no-untyped-def]
    from app.schemas.challenge import Constraint

    hard = Constraint(type="must_include_theme", value="fire", is_hard=True)
    assert engine.validate("Dragon fire bakery", [hard]).valid is True
    missing = engine.validate("Dragon bakery", [hard])
    assert missing.valid is False and missing.hard_violations

    soft = Constraint(type="must_include_theme", value="fire", is_hard=False)
    soft_missing = engine.validate("Dragon bakery", [soft])
    assert soft_missing.valid is True and soft_missing.soft_violations


def test_exactly_n_emojis(engine) -> None:  # type: ignore[no-untyped-def]
    from app.schemas.challenge import Constraint

    rule = Constraint(type="exactly_n_emojis", value=3, is_hard=True)
    assert engine.validate("☕️🌙✨ coffee", [rule]).valid is True
    result = engine.validate("☕️ coffee", [rule])
    assert result.valid is False and "found 1" in result.hard_violations[0]


def test_no_letter_e(engine) -> None:  # type: ignore[no-untyped-def]
    from app.schemas.challenge import Constraint

    rule = Constraint(type="no_letter_e", is_hard=True)
    assert engine.validate("Dragon佳作 🌙", [rule]).valid is True
    assert engine.validate("The bakery", [rule]).valid is False


def test_one_sentence_only(engine) -> None:  # type: ignore[no-untyped-def]
    from app.schemas.challenge import Constraint

    rule = Constraint(type="one_sentence_only", is_hard=True)
    assert engine.validate("One sentence only!", [rule]).valid is True
    assert engine.validate("Sentence one. Sentence two.", [rule]).valid is False


def test_must_rhyme_is_soft(engine) -> None:  # type: ignore[no-untyped-def]
    from app.schemas.challenge import Constraint

    rule = Constraint(type="must_rhyme", is_hard=False)
    rhyming = engine.validate("Fresh bread on the shelf, baked all by myself", [rule])
    assert rhyming.valid is True and rhyming.soft_violations == []

    not_rhyming = engine.validate("Come for the bread, stay for the flames", [rule])
    assert not_rhyming.valid is True and not_rhyming.soft_violations


def test_no_adjectives_is_soft_with_builtin_list(engine) -> None:  # type: ignore[no-untyped-def]
    from app.schemas.challenge import Constraint

    rule = Constraint(type="no_adjectives", is_hard=False)
    clean = engine.validate("Bread from the oven, sold by the loaf", [rule])
    assert clean.valid is True and clean.soft_violations == []

    flagged = engine.validate("Good bread, cheap prices, fresh loaves", [rule])
    assert flagged.valid is True
    assert any("good" in v for v in flagged.soft_violations)


def test_hard_and_soft_violations_are_sorted(engine) -> None:  # type: ignore[no-untyped-def]
    from app.schemas.challenge import Constraint

    constraints = [
        Constraint(type="max_words", value=2, is_hard=True),
        Constraint(type="no_adjectives", is_hard=False),
    ]
    result = engine.validate("good bread and butter cups", constraints)
    assert result.valid is False
    assert len(result.hard_violations) == 1
    assert len(result.soft_violations) == 1


# ---------------------------------------------------------------------------
# InputValidator


def test_input_validator() -> None:  # type: ignore[no-untyped-def]
    from app.services.input_validator import InputValidator

    validator = InputValidator()
    assert validator.validate(None, "text_single_line").valid is False
    assert validator.validate("   ", "text_single_line").valid is False
    assert validator.validate("ok", "text_single_line").valid is True
    assert validator.validate("line one\nline two", "text_single_line").valid is False
    assert validator.validate("line one\nline two", "text_multi_line").valid is True
    assert validator.validate("ok", "telepathy").valid is False


# ---------------------------------------------------------------------------
# ScoringEngine (Master Architecture §12.5)


def test_scoring_engine_formula(service) -> None:  # type: ignore[no-untyped-def]
    challenge = service.get_challenge("challenge_slogan_01")  # base 100, time 0.15, streak 0.05
    scoring = service.scoring_engine

    # Correct guess, no time, no streak -> base only.
    assert scoring.calculate_score(True, 0, 15, 0, challenge) == 100
    # Correct + partial time: 100 + int(100 * 0.15 * 5/15) = 105.
    assert scoring.calculate_score(True, 5, 15, 0, challenge) == 105
    # Correct + full time + streak 2: 100 + 15 + (2 * 100 * 0.05) = 125.
    assert scoring.calculate_score(True, 15, 15, 2, challenge) == 125
    # Wrong guess, no time, no streak -> zero.
    assert scoring.calculate_score(False, 0, 15, 0, challenge) == 0
    # Wrong guess still accrues time/streak components per §12.5's literal formula.
    assert scoring.calculate_score(False, 5, 15, 2, challenge) == int(5.0 + 10.0)
    # Negative remaining time clamps to zero.
    assert scoring.calculate_score(True, -3, 15, 0, challenge) == 100
