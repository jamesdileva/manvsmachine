"""Anthropic provider: fallback #1 external provider (Implementation Guide §6.3)."""

import httpx

from app.services.ai.providers.base import AIProvider, ProviderError, ProviderUnavailable

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    """Calls the Anthropic messages API; available whenever a key is set."""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307", timeout: int = 30) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

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
                ANTHROPIC_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                },
                json={
                    "model": self.model,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
        except httpx.TimeoutException as exc:
            raise ProviderUnavailable(f"anthropic timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"anthropic unreachable: {exc}") from exc

        if response.status_code != 200:
            raise ProviderError(
                f"anthropic returned {response.status_code}: {response.text[:200]}"
            )
        blocks = response.json()["content"]
        text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        return text.strip()

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "anthropic"

    async def aclose(self) -> None:
        await self.client.aclose()
