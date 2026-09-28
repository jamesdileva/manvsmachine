"""Scoring persistence: round scores, daily aggregation, ratings, streaks."""

import datetime as dt

from sqlalchemy import func
from sqlmodel import col, select

from app.db.models import Score, Streak, User, utc_now
from app.repositories.base import BaseRepository
from app.schemas.leaderboard import LeaderboardEntry

DEFAULT_RATING = 1000.0


class ScoringRepository(BaseRepository):
    async def create_score(
        self,
        user_id: str,
        round_id: str,
        base: int,
        time_bonus: int,
        streak_bonus: int,
        total: int,
    ) -> Score:
        score = Score(
            user_id=user_id,
            round_id=round_id,
            base_score=base,
            time_bonus=time_bonus,
            streak_bonus=streak_bonus,
            total_score=total,
        )
        await self._save(score)
        return score

    async def get_daily_scores(self, for_date: dt.date, limit: int = 100) -> list[LeaderboardEntry]:
        """Users ranked by total score earned on a date."""
        stmt = (
            select(Score.user_id, User.display_name, func.sum(Score.total_score).label("total"))
            .join(User, col(User.id) == Score.user_id)
            .where(func.date(Score.scored_at) == for_date)
            .group_by(Score.user_id, User.display_name)
            .order_by(func.sum(Score.total_score).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            LeaderboardEntry(
                rank=i + 1,
                user_id=user_id,
                display_name=display_name,
                score=int(total),
            )
            for i, (user_id, display_name, total) in enumerate(rows)
        ]

    async def get_user_rating(self, user_id: str) -> float:
        """Current Detection Rating; the default for unknown users."""
        user = await self.session.get(User, user_id)
        return user.detection_rating if user else DEFAULT_RATING

    async def update_streak(self, user_id: str, streak_type: str, count: int) -> Streak:
        """Upsert a streak counter; retains the longest record seen."""
        stmt = select(Streak).where(Streak.user_id == user_id, Streak.type == streak_type)
        streak = (await self.session.execute(stmt)).scalar_one_or_none()
        today = utc_now().date()
        if streak is None:
            streak = Streak(
                user_id=user_id,
                type=streak_type,
                count=count,
                last_active_date=today,
                longest_record=max(count, 0),
            )
        else:
            streak.count = count
            streak.last_active_date = today
            streak.longest_record = max(streak.longest_record, count)
        await self._save(streak)
        return streak
