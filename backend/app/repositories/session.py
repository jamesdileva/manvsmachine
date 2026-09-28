"""Play-session persistence."""


from sqlmodel import col, select

from app.db.models import Session, utc_now
from app.repositories.base import BaseRepository

VALID_SESSION_STATES = {"in_progress", "completed"}


class SessionRepository(BaseRepository):
    async def create(self, user_id: str, challenge_ids: list[str], is_daily: bool = False) -> Session:
        game_session = Session(user_id=user_id, challenge_ids=challenge_ids, is_daily=is_daily)
        await self._save(game_session)
        return game_session

    async def get(self, session_id: str) -> Session | None:
        return await self.session.get(Session, session_id)

    async def update_state(self, session_id: str, state: str) -> Session | None:
        """Session state is derived, not stored: 'completed' stamps completed_at."""
        if state not in VALID_SESSION_STATES:
            raise ValueError(f"invalid session state: {state!r}")
        game_session = await self.get(session_id)
        if game_session is None:
            return None
        game_session.completed_at = utc_now() if state == "completed" else None
        await self.session.commit()
        return game_session

    async def complete(self, session_id: str, final_score: int) -> Session | None:
        game_session = await self.get(session_id)
        if game_session is None:
            return None
        game_session.final_score = final_score
        game_session.completed_at = utc_now()
        await self.session.commit()
        return game_session

    async def get_user_sessions(self, user_id: str, limit: int = 20) -> list[Session]:
        """Most recent sessions for a user."""
        stmt = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(col(Session.started_at).desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())
