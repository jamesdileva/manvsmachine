"""In-process ephemeral state store (replaces Redis in the local MVP).

Single-process by design — the MVP is one player per session, so per-session
round/WebSocket state lives in memory. Never persisted; cleared on startup so
state never outlives a stale process.
"""

import threading


class StateStore:
    """Thread-safe key-value scratchpad for ephemeral state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, object]] = {}

    def get(self, key: str) -> dict[str, object] | None:
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: dict[str, object]) -> None:
        with self._lock:
            self._data[key] = value

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


state_store = StateStore()
