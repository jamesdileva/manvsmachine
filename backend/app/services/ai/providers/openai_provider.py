"""OpenAI provider: primary external provider (Implementation Guide §6.2)."""

import httpx

from app.services.ai.providers.base import AIProvider, ProviderError, ProviderUnavailable

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    """Calls the OpenAI chat completions API; available whenever a key is set."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout: int = 30) -> None:
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
                OPENAI_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
        except httpx.TimeoutException as exc:
            raise ProviderUnavailable(f"openai timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"openai unreachable: {exc}") from exc

        if response.status_code != 200:
            raise ProviderError(f"openai returned {response.status_code}: {response.text[:200]}")
        content = response.json()["choices"][0]["message"]["content"]
        return content.strip()

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "openai"

    async def aclose(self) -> None:
        await self.client.aclose()
