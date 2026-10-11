"""Share service and endpoint tests (Sprint 25 — Implementation Guide §2.6/§5.8)."""

import asyncio
import base64
import struct
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import settings
from app.core.security import create_access_token
from app.db import models
from app.db.connection import make_engine, run_migrations
from app.schemas.session import RoundSummary, SessionSummary
from app.services.share_service import ShareService

CHALLENGE_ID = "challenge_slogan_01"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _summary(total: int = 275, accuracy: float | None = 66.7) -> SessionSummary:
    return SessionSummary(
        session_id="session-1",
        type="daily",
        rounds_total=3,
        rounds_played=3,
        total_score=total,
        accuracy=accuracy,
        rounds=[
            RoundSummary(
                round_number=1,
                challenge_id=CHALLENGE_ID,
                vote="B",
                correct=True,
                score=115,
                humanity_human=100,
                humanity_ai=0,
            ),
            RoundSummary(
                round_number=2,
                challenge_id=CHALLENGE_ID,
                vote="A",
                correct=False,
                score=15,
                humanity_human=0,
                humanity_ai=100,
            ),
            RoundSummary(
                round_number=3,
                challenge_id=CHALLENGE_ID,
                vote="B",
                correct=True,
                score=total - 130,
                humanity_human=100,
                humanity_ai=0,
            ),
        ],
        streak=1,
    )


def _chunks(png: bytes) -> dict[str, bytes]:
    """Split a PNG into its chunks (signature is 8 bytes, IEND ends the stream)."""
    offset, found = 8, {}
    while offset < len(png) - 8:
        (length,) = struct.unpack(">I", png[offset : offset + 4])
        kind = png[offset + 4 : offset + 8].decode("ascii")
        found[kind] = png[offset + 8 : offset + 8 + length]
        offset += 12 + length
    return found


# ---------------------------------------------------------------------------
# ShareService (Implementation Guide §5.8)


def test_share_text_matches_the_documented_format() -> None:
    assert ShareService().generate_share_text(_summary()) == (
        "I scored 275 on today's Man vs. Machine daily challenge! "
        "Can you beat my accuracy? #ManVsMachine"
    )


def test_share_text_uses_a_practice_label_off_daily() -> None:
    summary = _summary()
    summary.type = "practice"
    text = ShareService().generate_share_text(summary)
    assert text == (
        "I scored 275 on today's Man vs. Machine practice challenge! "
        "Can you beat my accuracy? #ManVsMachine"
    )


def test_share_link_is_a_local_replay_route() -> None:
    assert ShareService().create_share_link("abc123") == "/s/abc123"


def test_share_image_is_a_structurally_valid_png() -> None:
    png = ShareService().generate_share_image(_summary())

    assert png[:8] == PNG_SIGNATURE
    chunks = _chunks(png)
    assert set(chunks) == {"IHDR", "IDAT", "IEND"}
    width, height, bit_depth, color_type = struct.unpack(">IIBB", chunks["IHDR"][:10])
    assert (width, height) == (600, 400)
    assert bit_depth == 8
    assert color_type == 2  # truecolor RGB
    # IDAT inflates to exactly one filter byte + one RGB triple per pixel.
    assert len(zlib.decompress(chunks["IDAT"])) == height * (1 + width * 3)


def test_share_image_is_deterministic() -> None:
    assert ShareService().generate_share_image(_summary()) == ShareService().generate_share_image(
        _summary()
    )


def test_share_image_card_layout_carries_the_stats() -> None:
    """The card is laid out from the summary: title, score, accuracy, humanity."""
    lines = ShareService().card_lines(_summary())

    flat = " ".join(lines)
    assert "MAN VS MACHINE" in flat
    assert "SCORE 275" in flat
    assert "67%" in flat  # accuracy, rounded
    assert any("HUMANITY" in line for line in lines)


# ---------------------------------------------------------------------------
# HTTP endpoints


def _seed_share_db(db_url: str) -> None:
    """One completed, scored single-round session owned by http-user."""

    async def seed() -> None:
        engine = make_engine(db_url)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            session.add(
                models.Challenge(
                    id=CHALLENGE_ID,
                    name="Tiny Tagline",
                    prompt="Write a slogan for a dragon-owned bakery.",
                    ai_prompt_template_id="v1.0",
                )
            )
            session.add(
                models.User(id="http-user", display_name="Player_Share", guest_id="guest-share")
            )
            await session.commit()
            session.add(
                models.Session(
                    id="session-1",
                    user_id="http-user",
                    challenge_ids=[CHALLENGE_ID],
                    is_daily=True,
                    completed_at=models.utc_now(),
                    rounds_played=1,
                    final_score=115,
                )
            )
            session.add(
                models.Session(
                    id="open-session",
                    user_id="http-user",
                    challenge_ids=[CHALLENGE_ID],
                    is_daily=True,
                    rounds_played=1,
                )
            )
            await session.commit()
            session.add(
                models.Round(
                    id="round-1",
                    session_id="session-1",
                    challenge_id=CHALLENGE_ID,
                    round_number=1,
                    state="scored",
                    completed_at=models.utc_now(),
                    human_entry_id="entry-h",
                    ai_entry_id="entry-a",
                    vote="B",
                    reveal_data={
                        "human_was": "B",
                        "ai_was": "A",
                        "vote": "B",
                        "vote_correct": True,
                        "humanity_human": 100,
                        "humanity_ai": 0,
                        "explanation": "Entry A was the AI — nice catch.",
                    },
                )
            )
            await session.commit()
            session.add(
                models.Entry(
                    id="entry-h",
                    round_id="round-1",
                    author_type="human",
                    content="Fire baked. Dragon approved.",
                )
            )
            session.add(
                models.Entry(
                    id="entry-a",
                    round_id="round-1",
                    author_type="ai",
                    content="Dragon's fire, fresh baked.",
                )
            )
            session.add(
                models.Score(
                    user_id="http-user",
                    round_id="round-1",
                    base_score=100,
                    time_bonus=15,
                    streak_bonus=0,
                    total_score=115,
                )
            )
            await session.commit()
        await engine.dispose()

    asyncio.run(seed())


@pytest.fixture
def share_db(tmp_path: Path) -> str:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'share.db').as_posix()}"
    run_migrations(db_url)
    _seed_share_db(db_url)
    return db_url


@pytest.fixture
def share_client(share_db: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", share_db)
    monkeypatch.setattr(settings, "stub_provider_only", True)
    from app import main

    with TestClient(main.app) as client:
        yield client


def test_post_share_result_returns_text_link_and_image(share_client: TestClient) -> None:
    token = create_access_token("http-user")
    response = share_client.post(
        "/api/v1/share/result",
        json={"session_id": "session-1", "format": "image"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["share_text"] == (
        "I scored 115 on today's Man vs. Machine daily challenge! "
        "Can you beat my accuracy? #ManVsMachine"
    )
    assert body["share_url"] == "/s/session-1"
    assert base64.b64decode(body["share_image"])[:8] == PNG_SIGNATURE


def test_post_share_result_requires_auth(share_client: TestClient) -> None:
    assert (
        share_client.post("/api/v1/share/result", json={"session_id": "session-1"}).status_code
        == 401
    )


def test_post_share_result_rejects_a_foreign_session(share_client: TestClient) -> None:
    response = share_client.post(
        "/api/v1/share/result",
        json={"session_id": "session-1"},
        headers={"Authorization": f"Bearer {create_access_token('someone-else')}"},
    )
    assert response.status_code == 404


def test_post_share_result_rejects_an_unfinished_session(share_client: TestClient) -> None:
    response = share_client.post(
        "/api/v1/share/result",
        json={"session_id": "open-session"},
        headers={"Authorization": f"Bearer {create_access_token('http-user')}"},
    )
    assert response.status_code == 400


def test_get_share_replay_serves_the_shared_result(share_client: TestClient) -> None:
    response = share_client.get(
        "/api/v1/share/s/session-1",
        headers={"Authorization": f"Bearer {create_access_token('http-user')}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["share_text"].startswith("I scored 115 on")
    assert body["share_url"] == "/s/session-1"
    assert body["summary"]["total_score"] == 115
    assert body["summary"]["rounds"][0]["human_entry"] == "Fire baked. Dragon approved."
    assert body["summary"]["rounds"][0]["ai_entry"] == "Dragon's fire, fresh baked."


def test_get_share_replay_is_readable_by_other_players(share_client: TestClient) -> None:
    """The link exists to be shared: any signed-in player can open it."""
    response = share_client.get(
        "/api/v1/share/s/session-1",
        headers={"Authorization": f"Bearer {create_access_token('stranger')}"},
    )
    assert response.status_code == 200
    assert "I scored 115" in response.json()["share_text"]


def test_get_share_replay_unknown_session_is_404(share_client: TestClient) -> None:
    response = share_client.get(
        "/api/v1/share/s/nope",
        headers={"Authorization": f"Bearer {create_access_token('http-user')}"},
    )
    assert response.status_code == 404


def test_get_share_replay_requires_auth(share_client: TestClient) -> None:
    assert share_client.get("/api/v1/share/s/session-1").status_code == 401
