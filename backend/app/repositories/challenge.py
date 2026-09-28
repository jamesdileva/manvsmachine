"""Challenge persistence: definitions and deterministic daily assignments."""

import datetime as dt

from sqlmodel import col, select

from app.db.models import Challenge, ChallengeDaily, utc_now
from app.repositories.base import BaseRepository


class ChallengeRepository(BaseRepository):
    async def create(self, challenge: Challenge) -> Challenge:
        """Insert a challenge definition (ChallengeCreate schema arrives in Sprint 7)."""
        await self._save(challenge)
        return challenge

    async def get_by_id(self, challenge_id: str) -> Challenge | None:
        return await self.session.get(Challenge, challenge_id)

    async def get_daily(self, for_date: dt.date) -> Challenge | None:
        """The challenge assigned to a date via challenge_daily (deterministic)."""
        stmt = (
            select(Challenge)
            .join(ChallengeDaily, col(ChallengeDaily.challenge_id) == col(Challenge.id))
            .where(ChallengeDaily.date == for_date)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_all_ids(self) -> list[str]:
        """All challenge IDs (for rotation)."""
        rows = (await self.session.execute(select(Challenge.id))).all()
        return [row[0] for row in rows]

    async def increment_daily_usage(self, challenge_id: str, for_date: dt.date | None = None) -> None:
        """Record that a challenge was used on a date (challenge_daily upsert; date is PK)."""
        day = for_date or utc_now().date()
        if await self.session.get(ChallengeDaily, day) is not None:
            return
        self.session.add(ChallengeDaily(date=day, challenge_id=challenge_id))
        await self.session.commit()
