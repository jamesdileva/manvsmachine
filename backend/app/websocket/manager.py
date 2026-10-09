"""WebSocket manager: connection lifecycle and per-session pub/sub dispatch.

In-process by design — the local MVP is one player per session, so a session's
connections are a topic; a broadcast reaches every socket on that topic. All
durable state lives in SQLite, so a dropped client can rejoin at any time.
"""

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class WebSocketManager:
    """Tracks live connections per session topic and broadcasts to them."""

    def __init__(self) -> None:
        self._topics: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Subscribe a socket to its session topic."""
        async with self._lock:
            self._topics[session_id].add(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        """Unsubscribe a socket; empty topics are dropped."""
        async with self._lock:
            self._topics[session_id].discard(websocket)
            if not self._topics[session_id]:
                self._topics.pop(session_id, None)

    async def broadcast(self, session_id: str, message: dict) -> None:
        """Deliver a message to every socket on the session topic."""
        async with self._lock:
            targets = list(self._topics.get(session_id, ()))
        for websocket in targets:
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001 — a dead socket must not break the broadcast
                await self.disconnect(session_id, websocket)

    def connection_count(self, session_id: str) -> int:
        """Live connections on a session topic (0 for unknown sessions)."""
        return len(self._topics.get(session_id, ()))


manager = WebSocketManager()
