"""AIService: orchestrates prompt construction, provider fallback, sanitization, audit.

Pipeline (Master Architecture §13.1): build_prompt -> select_provider ->
generate -> sanitize_response -> record_prompt -> return the sanitized entry.
A provider failure falls through the chain; a dirty response (meta mention,
injection, empty) is rejected and retried, then falls through too. StubProvider
sits last in the chain, so the game never breaks.
"""

from app.core.config import Settings
from app.schemas.challenge import ChallengeDefinition
from app.services.ai.providers import (
    AIProvider,
    ProviderError,
    ProviderUnavailable,
    build_provider_chain,
)
from app.services.content_filter import ContentFilter
from app.services.prompt_audit_service import PromptAuditService

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 100


class AIService:
    """Builds deterministic prompts and turns provider output into a safe entry."""

    def __init__(
        self,
        config: Settings,
        content_filter: ContentFilter,
        audit_service: PromptAuditService,
        providers: list[AIProvider] | None = None,
    ) -> None:
        self.config = config
        self.filter = content_filter
        self.audit = audit_service
        self.providers = providers if providers is not None else build_provider_chain(config)
        self.active_provider: AIProvider | None = None
        self._template = self.audit.get_prompt_template(self.audit.get_active_version())

    # ---------------------------------------------------------------------------
    # Prompt construction (fairness: a deterministic transformation of the challenge)

    def get_humanity_guidance(self, challenge: ChallengeDefinition) -> str:
        """Template humanity guidance plus this challenge's style guidance."""
        parts = list(self._template.humanity_guidance)
        if challenge.ai_prompt_guidance:
            parts.append(challenge.ai_prompt_guidance)
        return "\n".join(f"- {part}" for part in parts)

    def build_system_prompt(self, challenge: ChallengeDefinition) -> str:
        """v1.0 system prompt with the time limit and humanity guidance filled in."""
        system = self._template.system_prompt.format(time_limit=challenge.time_limit_seconds)
        guidance = self.get_humanity_guidance(challenge)
        return f"{system}\n\n{guidance}" if guidance else system

    def build_prompt(self, challenge: ChallengeDefinition) -> str:
        """The user prompt: challenge, formatted constraints, entry request."""
        return self._template.user_template.format(
            prompt=challenge.prompt,
            constraints_formatted=self._format_constraints(challenge),
            time_limit=challenge.time_limit_seconds,
        )

    @staticmethod
    def _format_constraints(challenge: ChallengeDefinition) -> str:
        return "\n".join(
            f"- {constraint.description or constraint.type}"
            + (f" ({constraint.value})" if constraint.value is not None else "")
            for constraint in challenge.constraints
        )

    # ---------------------------------------------------------------------------
    # Generation

    def select_provider(self) -> AIProvider:
        """First available provider in the chain (AGENTS.md core rule 10)."""
        for provider in self.providers:
            if provider.is_available():
                return provider
        raise ProviderUnavailable("no AI provider is available")

    async def generate_entry(
        self, challenge: ChallengeDefinition, retry_on_injection: int = 3
    ) -> str:
        """The sanitized AI entry for a challenge (raises only if the whole chain fails)."""
        system_prompt = self.build_system_prompt(challenge)
        prompt = self.build_prompt(challenge)
        last_error: ProviderError | None = None
        for provider in self.providers:
            if not provider.is_available():
                continue
            for _attempt in range(max(1, retry_on_injection)):
                try:
                    raw = await provider.generate(
                        prompt,
                        system_prompt,
                        temperature=DEFAULT_TEMPERATURE,
                        max_tokens=DEFAULT_MAX_TOKENS,
                        challenge_id=challenge.id,
                    )
                except ProviderError as exc:
                    last_error = exc
                    break  # provider failed: fall through the chain
                rejection = self._rejection(raw)
                if rejection is None:
                    return await self._accept(challenge, provider, prompt, system_prompt, raw)
                last_error = rejection
        raise ProviderUnavailable(f"no AI provider produced a valid entry: {last_error}")

    async def aclose(self) -> None:
        """Release provider HTTP clients (call at shutdown / end of a request)."""
        for provider in self.providers:
            close = getattr(provider, "aclose", None)
            if close is not None:
                await close()

    # ---------------------------------------------------------------------------
    # Internals

    def _rejection(self, raw: str) -> ProviderError | None:
        """Why this response cannot be used, or None when it is acceptable."""
        if not raw.strip():
            return ProviderError("empty AI response")
        mentions = self.filter.check_meta_mentions(raw)
        if mentions:
            return ProviderError(f"AI response contains meta-mentions: {mentions}")
        injection = self.filter.check_prompt_injection(raw)
        if injection.is_injection:
            return ProviderError(
                f"AI response looks like prompt injection: {injection.matched_patterns}"
            )
        return None

    async def _accept(
        self,
        challenge: ChallengeDefinition,
        provider: AIProvider,
        prompt: str,
        system_prompt: str,
        raw: str,
    ) -> str:
        entry = self.filter.sanitize_ai_response(raw)
        self.active_provider = provider
        await self.audit.record_usage(
            challenge_id=challenge.id,
            prompt=prompt,
            response=entry,
            provider=provider.get_provider_name(),
            model=provider.get_model_name(),
            raw_response=raw,
            system_prompt=system_prompt,
            prompt_version=self.audit.get_active_version(),
        )
        return entry
