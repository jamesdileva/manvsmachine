"""Ollama provider: local LLM option (Scope Constraint 7 — optional, not primary).

No API key, no external call. `think: false` is sent unconditionally: qwen3-family
models otherwise spend the entire token budget on hidden reasoning and return an
empty visible response (found in the Sprint 9 bake-off on this machine).
"""

import httpx

from app.services.ai.providers.base import AIProvider, ProviderError, ProviderUnavailable


class OllamaProvider(AIProvider):
    """Calls a local Ollama server's generate API; availability probes the server."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3.5:9b",
        timeout: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self._probe_client = httpx.Client(timeout=2)

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 100,
        *,
        challenge_id: str | None = None,
    ) -> str:
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "think": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            )
        except httpx.TimeoutException as exc:
            raise ProviderUnavailable(f"ollama timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"ollama unreachable: {exc}") from exc

        if response.status_code != 200:
            raise ProviderError(f"ollama returned {response.status_code}: {response.text[:200]}")
        return response.json().get("response", "").strip()

    def is_available(self) -> bool:
        """Cheap liveness probe — localhost round-trip, no model load."""
        try:
            return self._probe_client.get(f"{self.base_url}/api/version").status_code == 200
        except httpx.HTTPError:
            return False

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "ollama"

    async def aclose(self) -> None:
        await self.client.aclose()
        self._probe_client.close()
