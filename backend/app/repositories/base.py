"""Repository base: shared async session management."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel


class BaseRepository:
    """Owns the async session; each write operation commits on success."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _save(self, instance: SQLModel) -> None:
        """Persist a new or attached instance (add + commit)."""
        self.session.add(instance)
        await self.session.commit()
