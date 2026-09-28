"""Prompt audit persistence: versioned AI prompt + response records."""

from sqlmodel import col, select

from app.db.models import PromptAudit
from app.repositories.base import BaseRepository


class PromptAuditRepository(BaseRepository):
    async def record(
        self,
        prompt_version: str,
        prompt_system: str,
        prompt_user: str,
        challenge_id: str,
        ai_response: str,
        raw_response: str,
        provider: str,
        model: str,
        token_count: int | None = None,
    ) -> PromptAudit:
        """Log a prompt + response for audit/reproducibility."""
        row = PromptAudit(
            prompt_version=prompt_version,
            prompt_system=prompt_system,
            prompt_user=prompt_user,
            challenge_id=challenge_id,
            ai_response=ai_response,
            raw_response=raw_response,
            provider=provider,
            model=model,
            token_count=token_count,
        )
        await self._save(row)
        return row

    async def get_by_challenge(self, challenge_id: str) -> list[PromptAudit]:
        stmt = (
            select(PromptAudit)
            .where(PromptAudit.challenge_id == challenge_id)
            .order_by(col(PromptAudit.recorded_at))
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_versions(self) -> list[str]:
        """All distinct prompt versions in use."""
        rows = (
            await self.session.execute(
                select(PromptAudit.prompt_version).distinct().order_by(PromptAudit.prompt_version)
            )
        ).all()
        return [row[0] for row in rows]
