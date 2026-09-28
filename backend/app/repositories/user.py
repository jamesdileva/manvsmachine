"""User persistence: guests, ratings, display names, all-time leaderboard."""

from sqlmodel import col, select

from app.db.models import User, utc_now
from app.repositories.base import BaseRepository
from app.schemas.leaderboard import LeaderboardEntry


class UserRepository(BaseRepository):
    async def create(self, user: User) -> User:
        """Insert a user (guest or registered)."""
        await self._save(user)
        return user

    async def create_guest(self, display_name: str, guest_id: str | None = None) -> User:
        """Create a guest user (auto-generated name handled by the API layer)."""
        user = User(display_name=display_name, guest_id=guest_id)
        await self._save(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_guest_id(self, guest_id: str) -> User | None:
        stmt = select(User).where(User.guest_id == guest_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_rating(self, user_id: str, new_rating: float) -> User | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None
        user.detection_rating = new_rating
        user.updated_at = utc_now()
        await self.session.commit()
        return user

    async def update_display_name(self, user_id: str, name: str) -> User | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None
        user.display_name = name
        user.updated_at = utc_now()
        await self.session.commit()
        return user

    async def get_leaderboard(self, limit: int = 100) -> list[LeaderboardEntry]:
        """Top users ranked by Detection Rating."""
        stmt = select(User).order_by(col(User.detection_rating).desc()).limit(limit)
        users = (await self.session.execute(stmt)).scalars().all()
        return [
            LeaderboardEntry(
                rank=i + 1,
                user_id=user.id,
                display_name=user.display_name,
                rating=user.detection_rating,
            )
            for i, user in enumerate(users)
        ]
