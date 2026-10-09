"""WebSocket event handlers: auth, connect lifecycle, and client event dispatch.

Route: `/ws/session/{session_id}?token=<jwt>`. Auth happens before the socket is
accepted (bad token / unknown or foreign session -> close with 1008). Once
accepted, the client receives SESSION_STARTED + ROUND_START for the current
round and drives the game with SUBMIT_ENTRY / VOTE / PING; every server event is
broadcast to the session topic so multiple sockets stay in sync.
"""

from fastapi import Depends, Query, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import WS_1008_POLICY_VIOLATION
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.core.security import decode_token
from app.db.connection import get_session
from app.repositories.challenge import ChallengeRepository
from app.repositories.prompt_audit import PromptAuditRepository
from app.repositories.scoring import ScoringRepository
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.repositories.voting import VotingRepository
from app.schemas.session import ChallengeBrief, RoundState
from app.services.ai.providers import ProviderError
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.content_filter import ContentFilter
from app.services.prompt_audit_service import PromptAuditService
from app.services.scoring_service import ScoringService
from app.services.session_service import SessionService
from app.services.voting_service import VotingService
from app.websocket.manager import manager

SUBPROTOCOL = "manvs.protocol.v1"

# Client -> server events
EVENT_SUBMIT_ENTRY = "SUBMIT_ENTRY"
EVENT_VOTE = "VOTE"
EVENT_PING = "PING"

# Server -> client events
EVENT_SESSION_STARTED = "SESSION_STARTED"
EVENT_ROUND_START = "ROUND_START"
EVENT_AI_RESPONSE_READY = "AI_RESPONSE_READY"
EVENT_VOTE_CONFIRMED = "VOTE_CONFIRMED"
EVENT_REVEAL = "REVEAL"
EVENT_ROUND_SCORED = "ROUND_SCORED"
EVENT_SESSION_END = "SESSION_END"
EVENT_ERROR = "ERROR"
EVENT_PONG = "PONG"

_HANDLED_ERRORS = (AppError, ValueError, KeyError, ProviderError)


def _session_service(db: AsyncSession) -> SessionService:
    """Request-scoped SessionService wired to this connection's DB session."""
    return SessionService(
        SessionRepository(db),
        ChallengeService(ChallengeRepository(db)),
        AIService(
            settings,
            ContentFilter(),
            PromptAuditService(PromptAuditRepository(db)),
        ),
        VotingService(VotingRepository(db)),
        ScoringService(ScoringRepository(db), UserRepository(db)),
    )


async def session_socket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
) -> None:
    """Live game channel for one session: auth, greet, then the event loop."""
    try:
        user_id = decode_token(token)
    except AppError:
        await websocket.close(code=WS_1008_POLICY_VIOLATION, reason="invalid token")
        return

    service = _session_service(db)
    try:
        await service.get_session_overview(session_id, user_id)  # ownership + existence
    except NotFoundError:
        await websocket.close(code=WS_1008_POLICY_VIOLATION, reason="session not found")
        return

    offered = websocket.scope.get("subprotocols") or []
    await websocket.accept(subprotocol=SUBPROTOCOL if SUBPROTOCOL in offered else None)
    await manager.connect(session_id, websocket)
    try:
        await _greet(websocket, service, session_id, user_id)
        await _event_loop(websocket, service, session_id, user_id)
    finally:
        await manager.disconnect(session_id, websocket)


async def _greet(
    websocket: WebSocket, service: SessionService, session_id: str, user_id: str
) -> None:
    overview = await service.get_session_overview(session_id, user_id)
    await websocket.send_json(
        {
            "type": EVENT_SESSION_STARTED,
            "data": {
                "sessionId": overview.session_id,
                "rounds": overview.rounds_total,
                "roundsPlayed": overview.rounds_played,
                "completed": overview.completed,
                "challenges": [_challenge_data(c) for c in overview.challenges],
            },
        }
    )
    current = await service.start_next_round(session_id, user_id)
    if current is None:
        await _send_session_end(websocket, service, session_id, user_id)
    else:
        await websocket.send_json(
            {"type": EVENT_ROUND_START, "data": _round_start_data(current)}
        )


async def _event_loop(
    websocket: WebSocket, service: SessionService, session_id: str, user_id: str
) -> None:
    try:
        while True:
            message = await websocket.receive_json()
            event = message.get("type")
            data = message.get("data") or {}
            try:
                if event == EVENT_PING:
                    await manager.broadcast(session_id, {"type": EVENT_PONG, "data": {}})
                elif event == EVENT_SUBMIT_ENTRY:
                    submission = await service.submit_entry(
                        data["roundId"], data["entry"], user_id
                    )
                    await manager.broadcast(
                        session_id,
                        {
                            "type": EVENT_AI_RESPONSE_READY,
                            "data": {
                                "roundId": submission.round_id,
                                "entries": submission.entries,
                            },
                        },
                    )
                elif event == EVENT_VOTE:
                    await _handle_vote(service, session_id, user_id, data)
                else:
                    await manager.broadcast(
                        session_id,
                        {
                            "type": EVENT_ERROR,
                            "data": {
                                "code": "unknown_event",
                                "message": f"unknown event type: {event!r}",
                            },
                        },
                    )
            except _HANDLED_ERRORS as exc:
                # A bad move is reported, not fatal: the socket stays usable.
                await manager.broadcast(
                    session_id,
                    {
                        "type": EVENT_ERROR,
                        "data": {"code": type(exc).__name__, "message": str(exc)},
                    },
                )
    except WebSocketDisconnect:
        return  # the client closed the socket: normal end of the connection


async def _handle_vote(
    service: SessionService, session_id: str, user_id: str, data: dict
) -> None:
    round_id = data["roundId"]
    vote = data["vote"]
    # The vote is processed first: a rejected vote (wrong phase, bad letter)
    # surfaces as ERROR instead of a confirmation.
    result = await service.vote(round_id, user_id, vote)
    await manager.broadcast(
        session_id,
        {"type": EVENT_VOTE_CONFIRMED, "data": {"roundId": round_id, "vote": vote}},
    )
    reveal = result.reveal
    await manager.broadcast(
        session_id,
        {
            "type": EVENT_REVEAL,
            "data": {
                "roundId": round_id,
                "humanWas": reveal.human_was,
                "aiWas": reveal.ai_was,
                "vote": reveal.vote,
                "voteCorrect": reveal.vote_correct,
                "humanityHuman": reveal.humanity_human,
                "humanityAI": reveal.humanity_ai,
                "explanation": reveal.explanation,
            },
        },
    )
    await manager.broadcast(
        session_id,
        {
            "type": EVENT_ROUND_SCORED,
            "data": {
                "roundId": round_id,
                "score": {
                    "base": result.score.base,
                    "timeBonus": result.score.time_bonus,
                    "streakBonus": result.score.streak_bonus,
                    "total": result.score.total,
                },
                "ratingChange": result.rating_change,
                "streakUpdate": result.streak,
            },
        },
    )
    current = await service.start_next_round(session_id, user_id)
    if current is None:
        summary = await service.get_session_summary(session_id, user_id)
        await manager.broadcast(
            session_id,
            {
                "type": EVENT_SESSION_END,
                "data": {
                    "sessionId": session_id,
                    "summary": summary.model_dump(mode="json"),
                },
            },
        )
    else:
        await manager.broadcast(
            session_id,
            {"type": EVENT_ROUND_START, "data": _round_start_data(current)},
        )


async def _send_session_end(
    websocket: WebSocket, service: SessionService, session_id: str, user_id: str
) -> None:
    summary = await service.get_session_summary(session_id, user_id)
    await websocket.send_json(
        {
            "type": EVENT_SESSION_END,
            "data": {
                "sessionId": session_id,
                "summary": summary.model_dump(mode="json"),
            },
        }
    )


def _round_start_data(current: RoundState) -> dict:
    return {
        "roundId": current.round_id,
        "roundNumber": current.round_number,
        "roundsTotal": current.rounds_total,
        "challenge": _challenge_data(current.challenge),
        "timeLimitSeconds": current.challenge.time_limit_seconds,
        "state": current.state,
    }


def _challenge_data(brief: ChallengeBrief) -> dict:
    return {
        "id": brief.id,
        "prompt": brief.prompt,
        "timeLimitSeconds": brief.time_limit_seconds,
    }
