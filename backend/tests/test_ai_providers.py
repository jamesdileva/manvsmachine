"""AI provider tests (Sprint 9) — ABC contract, four providers, fallback chain."""

import json
from pathlib import Path

import httpx
import pytest

from app.core.config import settings
from app.services.ai.providers.anthropic_provider import AnthropicProvider
from app.services.ai.providers.base import AIProvider, ProviderError, ProviderUnavailable
from app.services.ai.providers.ollama_provider import OllamaProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.providers.stub_provider import STUB_DIR, StubProvider


def stub_pool(challenge_id: str = "challenge_slogan_01") -> list[str]:
    return json.loads((STUB_DIR / f"{challenge_id}.json").read_text(encoding="utf-8"))


def openai_handler(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content)
    assert payload["model"] == "gpt-4o-mini"
    assert payload["messages"][0] == {"role": "system", "content": "system text"}
    assert payload["messages"][1] == {"role": "user", "content": "the prompt"}
    assert payload["temperature"] == 0.7
    assert payload["max_tokens"] == 100
    return httpx.Response(200, json={"choices": [{"message": {"content": "  Fire baked.  "}}]})


def anthropic_handler(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content)
    assert payload["model"] == "claude-3-haiku-20240307"
    assert payload["system"] == "system text"
    assert payload["messages"][0] == {"role": "user", "content": "the prompt"}
    return httpx.Response(
        200, json={"content": [{"type": "text", "text": "  Dragon approved.  "}]}
    )


def ollama_handler(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content)
    assert payload["model"] == "qwen3.5:9b"
    assert payload["system"] == "system text"
    assert payload["prompt"] == "the prompt"
    assert payload["think"] is False  # qwen3-family burns tokens on hidden reasoning otherwise
    assert payload["stream"] is False
    assert payload["options"]["temperature"] == 0.7
    assert payload["options"]["num_predict"] == 100
    return httpx.Response(200, json={"response": "  Fire baked. Dragon approved.  "})


def swap_async_client(provider: object, transport: httpx.MockTransport) -> None:
    provider.client = httpx.AsyncClient(transport=transport)  # type: ignore[attr-defined]


def swap_sync_client(provider: object, transport: httpx.MockTransport) -> None:
    provider._probe_client = httpx.Client(transport=transport)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# ABC contract


async def test_stub_provider_is_always_available() -> None:
    assert StubProvider().is_available() is True


def test_providers_expose_names() -> None:
    openai = OpenAIProvider(api_key="sk-test")
    assert openai.get_provider_name() == "openai"
    assert openai.get_model_name() == "gpt-4o-mini"
    assert openai.is_available() is True
    assert OpenAIProvider(api_key="").is_available() is False

    anthropic = AnthropicProvider(api_key="sk-ant-test")
    assert anthropic.get_provider_name() == "anthropic"
    assert anthropic.get_model_name() == "claude-3-haiku-20240307"
    assert anthropic.is_available() is True
    assert AnthropicProvider(api_key="").is_available() is False

    assert OllamaProvider().get_provider_name() == "ollama"
    assert OllamaProvider(model="llama3.1:8b").get_model_name() == "llama3.1:8b"


# ---------------------------------------------------------------------------
# StubProvider


async def test_stub_provider_selects_from_challenge_pool() -> None:
    provider = StubProvider()
    pool = stub_pool()
    for prompt in ["slogan attempt one", "slogan attempt two", "slogan attempt three"]:
        entry = await provider.generate(prompt, "system", challenge_id="challenge_slogan_01")
        assert entry in pool


async def test_stub_provider_is_deterministic_by_prompt() -> None:
    provider = StubProvider()
    first = await provider.generate("same prompt", "system", challenge_id="challenge_slogan_01")
    second = await provider.generate("same prompt", "system", challenge_id="challenge_slogan_01")
    assert first == second

    # Different prompts spread across the pool (10 entries, 20 draws).
    draws = {
        await provider.generate(f"prompt {i}", "system", challenge_id="challenge_slogan_01")
        for i in range(20)
    }
    assert len(draws) > 1


async def test_stub_provider_uses_the_challenges_own_pool() -> None:
    provider = StubProvider()
    entry = await provider.generate("tell a movie plot", "system", challenge_id="challenge_emoji_03")
    assert entry in stub_pool("challenge_emoji_03")


async def test_stub_provider_unknown_challenge_raises() -> None:
    provider = StubProvider()
    with pytest.raises(ProviderError):
        await provider.generate("prompt", "system", challenge_id="challenge_missing_99")


async def test_stub_provider_requires_challenge_id() -> None:
    provider = StubProvider()
    with pytest.raises(ProviderError):
        await provider.generate("prompt", "system")


# ---------------------------------------------------------------------------
# OpenAIProvider


async def test_openai_generate_returns_content() -> None:
    provider = OpenAIProvider(api_key="sk-test")
    swap_async_client(provider, httpx.MockTransport(openai_handler))
    entry = await provider.generate("the prompt", "system text")
    assert entry == "Fire baked."


async def test_openai_generate_maps_errors() -> None:
    provider = OpenAIProvider(api_key="sk-test")

    swap_async_client(
        provider,
        httpx.MockTransport(lambda request: httpx.Response(401, json={"error": "bad key"})),
    )
    with pytest.raises(ProviderError):
        await provider.generate("the prompt", "system text")

    def refusing(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    swap_async_client(provider, httpx.MockTransport(refusing))
    with pytest.raises(ProviderUnavailable):
        await provider.generate("the prompt", "system text")


# ---------------------------------------------------------------------------
# AnthropicProvider


async def test_anthropic_generate_returns_content() -> None:
    provider = AnthropicProvider(api_key="sk-ant-test")
    swap_async_client(provider, httpx.MockTransport(anthropic_handler))
    entry = await provider.generate("the prompt", "system text")
    assert entry == "Dragon approved."


async def test_anthropic_generate_maps_errors() -> None:
    provider = AnthropicProvider(api_key="sk-ant-test")
    swap_async_client(
        provider,
        httpx.MockTransport(lambda request: httpx.Response(429, text="rate limited")),
    )
    with pytest.raises(ProviderError):
        await provider.generate("the prompt", "system text")


# ---------------------------------------------------------------------------
# OllamaProvider


def test_ollama_is_available_probes_the_server() -> None:
    provider = OllamaProvider(base_url="http://ollama.test")

    swap_sync_client(
        provider,
        httpx.MockTransport(lambda request: httpx.Response(200, json={"version": "0.40.0"})),
    )
    assert provider.is_available() is True

    swap_sync_client(provider, httpx.MockTransport(lambda request: httpx.Response(503)))
    assert provider.is_available() is False

    def refusing(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    swap_sync_client(provider, httpx.MockTransport(refusing))
    assert provider.is_available() is False


async def test_ollama_generate_returns_content() -> None:
    provider = OllamaProvider(base_url="http://ollama.test")
    swap_async_client(provider, httpx.MockTransport(ollama_handler))
    entry = await provider.generate("the prompt", "system text")
    assert entry == "Fire baked. Dragon approved."


async def test_ollama_generate_maps_connection_errors() -> None:
    provider = OllamaProvider(base_url="http://ollama.test")

    def refusing(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("server down")

    swap_async_client(provider, httpx.MockTransport(refusing))
    with pytest.raises(ProviderUnavailable):
        await provider.generate("the prompt", "system text")

    swap_async_client(
        provider,
        httpx.MockTransport(lambda request: httpx.Response(404, text="model not found")),
    )
    with pytest.raises(ProviderError):
        await provider.generate("the prompt", "system text")


# ---------------------------------------------------------------------------
# Provider chain + selection (Master Architecture §13.1)


def test_chain_orders_openai_anthropic_ollama_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai.providers import build_provider_chain

    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test")
    monkeypatch.setattr(settings, "stub_provider_only", False)
    chain = build_provider_chain()
    assert [provider.get_provider_name() for provider in chain] == [
        "openai",
        "anthropic",
        "ollama",
        "stub",
    ]


def test_chain_without_keys_is_ollama_then_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai.providers import build_provider_chain

    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "ollama_enabled", True)
    monkeypatch.setattr(settings, "stub_provider_only", False)
    chain = build_provider_chain()
    assert [provider.get_provider_name() for provider in chain] == ["ollama", "stub"]


def test_chain_stub_provider_only_forces_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai.providers import build_provider_chain

    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test")
    monkeypatch.setattr(settings, "ollama_enabled", True)
    monkeypatch.setattr(settings, "stub_provider_only", True)
    chain = build_provider_chain()
    assert [provider.get_provider_name() for provider in chain] == ["stub"]


def test_select_provider_falls_through_the_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai.providers import build_provider_chain, select_provider

    # No keys, Ollama disabled: the chain is [ollama(unavailable? no...), stub]
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "ollama_enabled", False)
    monkeypatch.setattr(settings, "stub_provider_only", False)
    selected = select_provider(build_provider_chain())
    assert isinstance(selected, StubProvider)

    # Ollama up: it wins over Stub (real generation beats canned text).
    monkeypatch.setattr(settings, "ollama_enabled", True)
    chain = build_provider_chain()
    ollama = next(p for p in chain if p.get_provider_name() == "ollama")
    swap_sync_client(
        ollama,
        httpx.MockTransport(lambda request: httpx.Response(200, json={"version": "0.40.0"})),
    )
    assert isinstance(select_provider(chain), OllamaProvider)

    # Ollama down: fall through to Stub — the game never breaks.
    swap_sync_client(
        ollama,
        httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("down"))
        ),
    )
    assert isinstance(select_provider(chain), StubProvider)


def test_abc_rejects_incomplete_providers() -> None:
    class Incomplete(AIProvider):
        pass

    with pytest.raises(TypeError):
        Incomplete()
