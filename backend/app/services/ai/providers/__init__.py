"""AI provider package: provider implementations and the fallback chain.

Chain order (Master Architecture §13.1 + Scope Constraint 7):
OpenAI (key) -> Anthropic (key) -> Ollama (local, optional) -> Stub (always).
`STUB_PROVIDER_ONLY=true` collapses the chain to Stub for E2E tests.
"""

from app.core.config import Settings, settings
from app.services.ai.providers.anthropic_provider import AnthropicProvider
from app.services.ai.providers.base import AIProvider, ProviderError, ProviderUnavailable
from app.services.ai.providers.ollama_provider import OllamaProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.providers.stub_provider import StubProvider

__all__ = [
    "AIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "ProviderError",
    "ProviderUnavailable",
    "StubProvider",
    "build_provider_chain",
    "select_provider",
]


def build_provider_chain(config: Settings | None = None) -> list[AIProvider]:
    """The ordered provider list for the current configuration."""
    config = config or settings
    if config.stub_provider_only:
        return [StubProvider()]
    chain: list[AIProvider] = []
    if config.openai_api_key:
        chain.append(OpenAIProvider(api_key=config.openai_api_key))
    if config.anthropic_api_key:
        chain.append(AnthropicProvider(api_key=config.anthropic_api_key))
    if config.ollama_enabled:
        chain.append(OllamaProvider(base_url=config.ollama_base_url, model=config.ollama_model))
    chain.append(StubProvider())
    return chain


def select_provider(providers: list[AIProvider]) -> AIProvider:
    """First available provider in the chain (Stub is always last and available)."""
    for provider in providers:
        if provider.is_available():
            return provider
    raise ProviderUnavailable("no AI provider is available")
