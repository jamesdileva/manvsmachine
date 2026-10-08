"""AI provider interface: the one contract every provider implements.

Fallback is mandatory (AGENTS.md core rule 10): AIService tries providers in
chain order and moves on when one raises. `ProviderUnavailable` (a subclass of
`ProviderError`) marks providers that are down or misconfigured so the chain
distinguishes "try the next one" from "this provider is broken".
"""

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """A provider call failed (bad response, non-2xx, missing stub pool)."""


class ProviderUnavailable(ProviderError):
    """The provider could not be reached at all (connection/timeout/refused)."""


class AIProvider(ABC):
    """Generates a single entry for a challenge from a system + user prompt."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 100,
        *,
        challenge_id: str | None = None,
    ) -> str:
        """Raw (unsanitized) entry text for the prompt.

        `challenge_id` is optional metadata; the StubProvider requires it to
        pick the right entry pool.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider can serve requests right now."""

    @abstractmethod
    def get_model_name(self) -> str:
        """The model identifier this provider will use."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Short provider key: "openai", "anthropic", "ollama", "stub"."""
