"""Sprint 24: end-to-end game flow with StubProvider (Implementation Guide §12.4).

Walks a stakeholder through a complete 3-round game over the real HTTP +
WebSocket stack with no AI API keys: guest auth → session start → connect →
submit → anonymized A/B → vote → reveal → score → summary → leaderboard →
share result + replay link.

All thirteen steps of the guide's flow (Master Architecture §21's ten plus the
guide's own 12 and 13) are covered by `test_full_game_flow_with_stub_provider`
plus the focused tests below it.
"""

import base64
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

# Practice session with fixed challenge ids (the daily rotation changes by date).
CHALLENGE_IDS = ["challenge_slogan_01", "challenge_emoji_03", "challenge_tweet_09"]
# baseScore per challenge definition — the guess component on a correct vote.
BASE_SCORES = {
    "challenge_slogan_01": 100,
    "challenge_emoji_03": 120,
    "challenge_tweet_09": 110,
}
# Per-challenge entries that satisfy each round's hard constraints; none of
# them appear in the stub pools, so the A/B letters stay unambiguous.
ENTRIES = {
    "challenge_slogan_01": "Bread baked by a dragon",
    "challenge_emoji_03": "\U0001F525\U0001F35E\U0001F432\U0001F60B✨",
    "challenge_tweet_09": "My houseplant is judging me and I accept it",
}

STUB_ENTRIES_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "stub_entries"


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    """One app instance for the whole E2E suite, on its own throwaway database.

    E2E flows need a single event loop: each TestClient runs its own loop in its
    own thread, and the app's module-level WebSocket manager holds an
    `asyncio.Lock` bound to whichever loop first awaited it. Building several
    TestClients in one process leaves that lock and the pooled SQLite
    connections attached to a dead loop, which stalls later broadcasts. Sharing
    one instance across the module keeps the suite on one loop — exactly as a
    real player's single browser session would be.
    """
    db_file = tmp_path_factory.mktemp("e2e") / "e2e.db"
    original = (
        settings.database_url,
        settings.stub_provider_only,
        settings.ollama_enabled,
    )
    settings.database_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    settings.stub_provider_only = True
    settings.ollama_enabled = False
    from app import main

    with TestClient(main.app) as test_client:
        yield test_client
    (
        settings.database_url,
        settings.stub_provider_only,
        settings.ollama_enabled,
    ) = original


def _guest(client) -> dict:
    response = client.post("/api/v1/auth/guest", json={})
    assert response.status_code == 201, response.text
    return response.json()


def _start_session(client, token: str) -> dict:
    """§12.4 step 2: create a session with the three practice challenges."""
    response = client.post(
        "/api/v1/session/start",
        json={"type": "practice", "challenge_ids": CHALLENGE_IDS},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _ws_url(session_id: str, token: str) -> str:
    return f"/ws/session/{session_id}?token={token}"


def _submit_and_vote(ws, round_id: str, entry: str) -> dict:
    """Steps 5-10 for one round: submit → anonymized A/B → vote → reveal → score."""
    ws.send_json({"type": "SUBMIT_ENTRY", "data": {"roundId": round_id, "entry": entry}})
    ready = ws.receive_json()
    assert ready["type"] == "AI_RESPONSE_READY", ready

    entries = ready["data"]["entries"]
    assert set(entries) == {"A", "B"}
    assert entry in entries.values()
    ai_entry = next(text for text in entries.values() if text != entry)
    # Step 7: the payload carries only the round id and A/B letters — nothing
    # labels which side is the player's own entry.
    assert set(ready["data"]) == {"roundId", "entries"}

    ai_letter = "B" if entries["A"] == entry else "A"
    ws.send_json({"type": "VOTE", "data": {"roundId": round_id, "vote": ai_letter}})

    events = {}
    for expected in ("VOTE_CONFIRMED", "REVEAL", "ROUND_SCORED"):
        message = ws.receive_json()
        assert message["type"] == expected, message
        events[expected] = message["data"]
    return {"ai_entry": ai_entry, "ai_letter": ai_letter, **events}


def test_full_game_flow_with_stub_provider(client) -> None:
    """§12.4 steps 1-12: a complete 3-round game with the StubProvider only."""
    # §12.4 step 1: the backend runs with STUB_PROVIDER_ONLY — no AI keys exist.
    assert settings.stub_provider_only is True

    guest = _guest(client)
    token = guest["token"]
    display_name = guest["display_name"]
    started = _start_session(client, token)

    round_totals: list[int] = []
    with client.websocket_connect(_ws_url(started["session_id"], token)) as ws:
        # Step 3-4: the handshake greets with the session and its first round.
        greeting = ws.receive_json()
        assert greeting["type"] == "SESSION_STARTED"
        assert greeting["data"]["sessionId"] == started["session_id"]
        assert greeting["data"]["rounds"] == 3
        assert {c["id"] for c in greeting["data"]["challenges"]} == set(CHALLENGE_IDS)

        for round_number in (1, 2, 3):
            round_start = ws.receive_json()
            assert round_start["type"] == "ROUND_START"
            data = round_start["data"]
            assert data["roundNumber"] == round_number
            assert data["roundsTotal"] == 3
            assert data["timeLimitSeconds"] >= 10
            challenge_id = data["challenge"]["id"]
            assert challenge_id in CHALLENGE_IDS

            result = _submit_and_vote(ws, data["roundId"], ENTRIES[challenge_id])

            # Step 9: the reveal attributes each letter correctly.
            reveal = result["REVEAL"]
            assert reveal["voteCorrect"] is True
            assert reveal["aiWas"] == result["ai_letter"]
            assert reveal["humanWas"] != reveal["aiWas"]
            assert 0 <= reveal["humanityHuman"] <= 100
            assert 0 <= reveal["humanityAI"] <= 100
            assert reveal["explanation"]

            # Step 10: the score matches the challenge's rules and the rating moves.
            score = result["ROUND_SCORED"]["score"]
            assert score["base"] == BASE_SCORES[challenge_id]
            assert score["total"] == (
                score["base"] + score["timeBonus"] + score["streakBonus"]
            )
            assert result["ROUND_SCORED"]["ratingChange"] != 0
            assert result["ROUND_SCORED"]["streakUpdate"] >= 1
            round_totals.append(score["total"])

        # Step 11: after round 3 the session ends with a summary.
        end = ws.receive_json()
        assert end["type"] == "SESSION_END"
        summary = end["data"]["summary"]
        assert summary["total_score"] == sum(round_totals)
        assert len(summary["rounds"]) == 3
        assert summary["accuracy"] == 100
        assert summary["streak"] >= 3

    # Step 12: the player appears on today's leaderboard with the session total.
    daily = client.get("/api/v1/leaderboard/daily")
    assert daily.status_code == 200
    board = daily.json()
    top = next(e for e in board["entries"] if e["display_name"] == display_name)
    assert top["rank"] == 1
    assert top["score"] == summary["total_score"]
    assert top["accuracy"] == 100

    # The rating, rounds, accuracy, and streaks all reflect the played game.
    profile = client.get(
        "/api/v1/profile", headers={"Authorization": f"Bearer {token}"}
    )
    assert profile.status_code == 200, profile.text
    stats = profile.json()
    assert stats["display_name"] == display_name
    assert stats["total_rounds"] == 3
    assert stats["overall_accuracy"] == 100
    assert stats["current_streak"] == 3
    assert stats["detection_rating"] != 1000.0

    # Step 13: the finished session produces a shareable result + viewable link.
    shared = client.post(
        "/api/v1/share/result",
        json={"session_id": started["session_id"], "format": "image"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert shared.status_code == 200, shared.text
    card = shared.json()
    assert card["share_text"] == (
        f"I scored {summary['total_score']} on today's Man vs. Machine practice "
        "challenge! Can you beat my accuracy? #ManVsMachine"
    )
    assert card["share_url"] == f"/s/{started['session_id']}"
    assert base64.b64decode(card["share_image"])[:8] == b"\x89PNG\r\n\x1a\n"

    replay = client.get(
        f"/api/v1/share/s/{started['session_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert replay.status_code == 200, replay.text
    body = replay.json()
    assert body["summary"]["total_score"] == summary["total_score"]
    assert len(body["summary"]["rounds"]) == 3
    assert all(round_entry["human_entry"] for round_entry in body["summary"]["rounds"])
    assert all(round_entry["ai_entry"] for round_entry in body["summary"]["rounds"])


def test_ai_entry_is_generated_from_the_stub_pool(client) -> None:
    """Step 6/DoD: the AI entry comes from the stub pool — no external provider."""
    token = _guest(client)["token"]
    started = _start_session(client, token)
    with client.websocket_connect(_ws_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        round_id = ws.receive_json()["data"]["roundId"]
        result = _submit_and_vote(ws, round_id, ENTRIES["challenge_slogan_01"])

    pool = json.loads(
        (STUB_ENTRIES_DIR / "challenge_slogan_01.json").read_text(encoding="utf-8")
    )
    assert result["ai_entry"] in pool


def test_ai_entries_stay_within_the_sanitization_contract(client, ai_responses) -> None:
    """The delivered AI entry obeys the content-filter rules from the fixtures."""
    token = _guest(client)["token"]
    started = _start_session(client, token)
    with client.websocket_connect(_ws_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        round_id = ws.receive_json()["data"]["roundId"]
        result = _submit_and_vote(ws, round_id, ENTRIES["challenge_slogan_01"])

    assert len(result["ai_entry"]) <= ai_responses["max_length"]
    lowered = result["ai_entry"].lower()
    for pattern in ai_responses["forbidden_patterns"]:
        assert pattern.lower() not in lowered


def test_challenge_definitions_match_the_fixture_contract(client, expected_challenges) -> None:
    """Served definitions stay semantically equal to the fixtures used by this suite."""
    from app.schemas.challenge import ChallengeDefinition

    assert set(expected_challenges) == set(CHALLENGE_IDS)
    for challenge_id, expected in expected_challenges.items():
        response = client.get(f"/api/v1/challenges/{challenge_id}")
        assert response.status_code == 200, response.text
        assert ChallengeDefinition.model_validate(response.json()) == (
            ChallengeDefinition.model_validate(expected)
        )


def test_e2e_needs_no_real_provider_configuration(client) -> None:
    """Step 1: STUB_PROVIDER_ONLY collapses the chain without any API keys."""
    from app.services.ai.providers import build_provider_chain, select_provider

    chain = build_provider_chain(settings)
    selected = select_provider(chain)
    assert selected.get_provider_name() == "stub"
    assert not settings.openai_api_key
    assert not settings.anthropic_api_key

