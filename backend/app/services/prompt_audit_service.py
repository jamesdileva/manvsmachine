"""Prompt audit service: versioned prompt templates and the audit trail.

Templates live as version-keyed JSON in `app/data/ai_prompts/` (Master
Architecture §13.4); every AI prompt + response used in a round is recorded via
PromptAuditRepository (§8: the AI prompt must be auditable).
"""

import json
from pathlib import Path

from app.core.config import settings
from app.db.models import PromptAudit
from app.repositories.prompt_audit import PromptAuditRepository
from app.schemas.prompt import PromptTemplate

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "data" / "ai_prompts"


class PromptAuditService:
    """Loads prompt templates by version and records every prompt + response pair."""

    def __init__(
        self,
        repo: PromptAuditRepository,
        prompts_dir: Path | None = None,
        active_version: str | None = None,
    ) -> None:
        self.repo = repo
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._active_version = active_version or settings.ai_prompt_version

    def get_prompt_template(self, version: str) -> PromptTemplate:
        """Load a version's template from disk (KeyError for unknown versions — a bug, not input)."""
        path = self.prompts_dir / f"{version}.json"
        if not path.is_file():
            raise KeyError(f"unknown prompt version: {version}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return PromptTemplate.model_validate(data)

    def get_active_version(self) -> str:
        """The configured active version (`AI_PROMPT_VERSION`, Master Architecture §13.4)."""
        return self._active_version

    def list_versions(self) -> list[str]:
        """Prompt template versions available on disk, sorted."""
        return sorted(path.stem for path in self.prompts_dir.glob("*.json"))

    async def record_usage(
        self,
        challenge_id: str,
        prompt: str,
        response: str,
        provider: str,
        model: str,
        token_count: int | None = None,
        raw_response: str | None = None,
        prompt_version: str | None = None,
        system_prompt: str | None = None,
    ) -> PromptAudit:
        """Record a prompt + response pair for audit/reproducibility (§8).

        `response` is the sanitized entry; `raw_response` keeps the provider's
        original output for debugging (defaults to the sanitized response).
        `system_prompt` overrides the template's system prompt when the caller
        sent a transformed one (AIService appends per-challenge guidance).
        """
        version = prompt_version or self.get_active_version()
        template = self.get_prompt_template(version)
        return await self.repo.record(
            prompt_version=version,
            prompt_system=(
                system_prompt if system_prompt is not None else template.system_prompt
            ),
            prompt_user=prompt,
            challenge_id=challenge_id,
            ai_response=response,
            raw_response=response if raw_response is None else raw_response,
            provider=provider,
            model=model,
            token_count=token_count,
        )
