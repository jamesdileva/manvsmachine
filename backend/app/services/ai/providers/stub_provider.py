"""Stub provider: the final fallback — pre-written entries, never breaks.

Loads the per-challenge pools in `app/data/stub_entries/` and selects
deterministically by prompt hash, so a given prompt always yields the same
entry (reproducible rounds, no API keys needed).
"""

import hashlib
import json
from pathlib import Path

from app.services.ai.providers.base import AIProvider, ProviderError

# app/services/ai/providers -> app/
STUB_DIR = Path(__file__).resolve().parents[3] / "data" / "stub_entries"


class StubProvider(AIProvider):
    """Serves entries from the static stub pools; always available."""

    def __init__(self, stub_dir: Path | None = None) -> None:
        self.stub_dir = stub_dir or STUB_DIR

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 100,
        *,
        challenge_id: str | None = None,
    ) -> str:
        if challenge_id is None:
            raise ProviderError("StubProvider needs a challenge_id to pick its entry pool")
        pool = self._load_pool(challenge_id)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return pool[int(digest, 16) % len(pool)]

    def is_available(self) -> bool:
        return True

    def get_model_name(self) -> str:
        return "stub-v1"

    def get_provider_name(self) -> str:
        return "stub"

    def _load_pool(self, challenge_id: str) -> list[str]:
        path = self.stub_dir / f"{challenge_id}.json"
        if not path.is_file():
            raise ProviderError(f"no stub pool for challenge: {challenge_id}")
        pool = json.loads(path.read_text(encoding="utf-8"))
        if not pool:
            raise ProviderError(f"empty stub pool for challenge: {challenge_id}")
        return pool
