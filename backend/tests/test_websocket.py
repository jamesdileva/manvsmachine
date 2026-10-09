"""WebSocket layer tests (Sprint 14) — auth, event flow, pub/sub, rejoin."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings

ENTRY = "Bread baked by a dragon"  # not in the stub pool (avoids A/B ambiguity)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_file = tmp_path / "ws.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    monkeypatch.setattr(settings, "stub_provider_only", True)
    monkeypatch.setattr(settings, "ollama_enabled", False)
    from app import main

    with TestClient(main.app) as test_client:
        yield test_client


def _token(client: TestClient) -> str:
    return client.post("/api/v1/auth/guest", json={}).json()["token"]


def _start_session(client: TestClient, token: str, practice: bool = False) -> dict:
    body = (
        {
            "type": "practice",
            "challenge_ids": [
                "challenge_slogan_01",
                "challenge_emoji_03",
                "challenge_tweet_09",
            ],
        }
        if practice
        else {"type": "daily"}
    )
    response = client.post(
        "/api/v1/session/start",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _url(session_id: str, token: str) -> str:
    return f"/ws/session/{session_id}?token={token}"


# ---------------------------------------------------------------------------
# Connection + auth


def test_connect_sends_session_started_and_round_start(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)

    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        first = ws.receive_json()
        assert first["type"] == "SESSION_STARTED"
        assert first["data"]["sessionId"] == started["session_id"]
        assert first["data"]["rounds"] == 3
        assert len(first["data"]["challenges"]) == 3

        second = ws.receive_json()
        assert second["type"] == "ROUND_START"
        assert second["data"]["roundId"] == started["round_id"]
        assert second["data"]["roundNumber"] == 1
        assert second["data"]["challenge"]["id"]
        assert second["data"]["timeLimitSeconds"] >= 10


def test_invalid_token_is_rejected(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(_url(started["session_id"], "not-a-token")):
            pass


def test_missing_token_is_rejected(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/session/{started['session_id']}"):
            pass


def test_unknown_session_is_rejected(client: TestClient) -> None:
    token = _token(client)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(_url("session-missing", token)):
            pass


def test_foreign_session_is_rejected(client: TestClient) -> None:
    owner_token = _token(client)
    stranger_token = _token(client)
    started = _start_session(client, owner_token)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(_url(started["session_id"], stranger_token)):
            pass


# ---------------------------------------------------------------------------
# Events


def test_ping_gets_pong(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)
    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        assert ws.receive_json()["type"] == "ROUND_START"
        ws.send_json({"type": "PING"})
        assert ws.receive_json()["type"] == "PONG"


def test_submit_entry_readies_the_ai_entry(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)
    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        assert ws.receive_json()["type"] == "ROUND_START"

        ws.send_json(
            {
                "type": "SUBMIT_ENTRY",
                "data": {
                    "sessionId": started["session_id"],
                    "roundId": started["round_id"],
                    "entry": ENTRY,
                },
            }
        )
        ready = ws.receive_json()
        assert ready["type"] == "AI_RESPONSE_READY"
        entries = ready["data"]["entries"]
        assert set(entries) == {"A", "B"}
        assert ENTRY in entries.values()


def test_full_round_flow(client: TestClient) -> None:
    token = _token(client)
    # Practice with the slogan challenge: the daily rotation changes daily, and
    # the score assertions need the known base of 100 / 15s limit.
    started = _start_session(client, token, practice=True)
    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        round_start = ws.receive_json()
        assert round_start["type"] == "ROUND_START"
        round_id = round_start["data"]["roundId"]

        ws.send_json(
            {"type": "SUBMIT_ENTRY", "data": {"roundId": round_id, "entry": ENTRY}}
        )
        ready = ws.receive_json()
        entries = ready["data"]["entries"]
        ai_letter = "B" if entries["A"] == ENTRY else "A"

        ws.send_json({"type": "VOTE", "data": {"roundId": round_id, "vote": ai_letter}})

        confirmed = ws.receive_json()
        assert confirmed["type"] == "VOTE_CONFIRMED"
        assert confirmed["data"]["vote"] == ai_letter

        reveal = ws.receive_json()
        assert reveal["type"] == "REVEAL"
        assert reveal["data"]["humanWas"] != reveal["data"]["aiWas"]
        assert reveal["data"]["explanation"]
        assert 0 <= reveal["data"]["humanityAI"] <= 100

        scored = ws.receive_json()
        assert scored["type"] == "ROUND_SCORED"
        assert scored["data"]["score"]["base"] == 100  # the AI was detected
        assert scored["data"]["score"]["total"] == (
            scored["data"]["score"]["base"]
            + scored["data"]["score"]["timeBonus"]
            + scored["data"]["score"]["streakBonus"]
        )
        assert scored["data"]["ratingChange"] != 0
        assert scored["data"]["streakUpdate"] >= 1

        next_round = ws.receive_json()
        assert next_round["type"] == "ROUND_START"
        assert next_round["data"]["roundNumber"] == 2


def test_session_end_after_three_rounds(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)
    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        for _ in range(3):
            round_start = ws.receive_json()
            round_id = round_start["data"]["roundId"]
            ws.send_json(
                {"type": "SUBMIT_ENTRY", "data": {"roundId": round_id, "entry": ENTRY}}
            )
            ready = ws.receive_json()
            entries = ready["data"]["entries"]
            ai_letter = "B" if entries["A"] == ENTRY else "A"
            ws.send_json({"type": "VOTE", "data": {"roundId": round_id, "vote": ai_letter}})
            for expected in ("VOTE_CONFIRMED", "REVEAL", "ROUND_SCORED"):
                assert ws.receive_json()["type"] == expected

        end = ws.receive_json()
        assert end["type"] == "SESSION_END"
        assert end["data"]["sessionId"] == started["session_id"]
        summary = end["data"]["summary"]
        assert summary["total_score"] > 0
        assert summary["accuracy"] == 100.0
        assert len(summary["rounds"]) == 3


def test_vote_in_wrong_state_sends_error_but_keeps_the_connection(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)
    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        assert ws.receive_json()["type"] == "ROUND_START"

        ws.send_json(
            {"type": "VOTE", "data": {"roundId": started["round_id"], "vote": "A"}}
        )
        error = ws.receive_json()
        assert error["type"] == "ERROR"
        assert error["data"]["code"]
        assert error["data"]["message"]

        # Still usable: the round flow continues after the error.
        ws.send_json(
            {"type": "SUBMIT_ENTRY", "data": {"roundId": started["round_id"], "entry": ENTRY}}
        )
        assert ws.receive_json()["type"] == "AI_RESPONSE_READY"


def test_unknown_event_type_sends_error(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)
    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        assert ws.receive_json()["type"] == "ROUND_START"
        ws.send_json({"type": "NOT_A_THING", "data": {}})
        error = ws.receive_json()
        assert error["type"] == "ERROR"


# ---------------------------------------------------------------------------
# Pub/sub + rejoin


def test_both_connections_receive_the_broadcast(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)
    with client.websocket_connect(_url(started["session_id"], token)) as first:
        with client.websocket_connect(_url(started["session_id"], token)) as second:
            for ws in (first, second):
                assert ws.receive_json()["type"] == "SESSION_STARTED"
                assert ws.receive_json()["type"] == "ROUND_START"

            # One client submits; the other receives the same broadcast (pub/sub).
            first.send_json(
                {
                    "type": "SUBMIT_ENTRY",
                    "data": {"roundId": started["round_id"], "entry": ENTRY},
                }
            )
            for ws in (first, second):
                ready = ws.receive_json()
                assert ready["type"] == "AI_RESPONSE_READY"
                assert ENTRY in ready["data"]["entries"].values()


def test_rejoin_resumes_the_current_round(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)

    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        assert ws.receive_json()["type"] == "ROUND_START"
        ws.send_json(
            {"type": "SUBMIT_ENTRY", "data": {"roundId": started["round_id"], "entry": ENTRY}}
        )
        assert ws.receive_json()["type"] == "AI_RESPONSE_READY"

    # Reconnect: state lives in SQLite, so the session resumes mid-round.
    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        round_start = ws.receive_json()
        assert round_start["type"] == "ROUND_START"
        assert round_start["data"]["roundId"] == started["round_id"]
        assert round_start["data"]["state"] == "voting"


def test_connecting_to_a_finished_session_ends_it(client: TestClient) -> None:
    token = _token(client)
    started = _start_session(client, token)
    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        for _ in range(3):
            round_start = ws.receive_json()
            round_id = round_start["data"]["roundId"]
            ws.send_json(
                {"type": "SUBMIT_ENTRY", "data": {"roundId": round_id, "entry": ENTRY}}
            )
            ready = ws.receive_json()
            ai_letter = "B" if ready["data"]["entries"]["A"] == ENTRY else "A"
            ws.send_json({"type": "VOTE", "data": {"roundId": round_id, "vote": ai_letter}})
            for expected in ("VOTE_CONFIRMED", "REVEAL", "ROUND_SCORED"):
                assert ws.receive_json()["type"] == expected
        assert ws.receive_json()["type"] == "SESSION_END"

    # Reconnecting to the completed session immediately replays the end state.
    with client.websocket_connect(_url(started["session_id"], token)) as ws:
        assert ws.receive_json()["type"] == "SESSION_STARTED"
        end = ws.receive_json()
        assert end["type"] == "SESSION_END"
        assert end["data"]["summary"]["rounds_played"] == 3


# ---------------------------------------------------------------------------
# WebSocketManager unit


async def test_manager_drops_dead_sockets() -> None:
    from app.websocket.manager import WebSocketManager

    class DeadSocket:
        async def send_json(self, message: dict) -> None:
            raise RuntimeError("socket is gone")

    manager = WebSocketManager()
    dead = DeadSocket()
    await manager.connect("session-1", dead)
    assert manager.connection_count("session-1") == 1
    await manager.broadcast("session-1", {"type": "PONG"})
    assert manager.connection_count("session-1") == 0  # cleaned up, no crash
    await manager.disconnect("session-1", dead)  # idempotent
    assert manager.connection_count("session-1") == 0
