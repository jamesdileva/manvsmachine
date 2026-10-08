"""Scoring persistence: round scores, daily aggregation, ratings, streaks."""

import datetime as dt

from sqlalchemy import case, func, or_
from sqlmodel import col, select

from app.db.models import (
    HumanityScore,
    LeaderboardSnapshot,
    Round,
    Score,
    Session,
    Streak,
    User,
    utc_now,
)
from app.repositories.base import BaseRepository
from app.schemas.leaderboard import LeaderboardEntry

DEFAULT_RATING = 1000.0

VALID_VOTE_LETTERS = {"A", "B"}


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
        """Users ranked by total score earned on a date, with same-date accuracy.

        Accuracy comes from the base component (100 on a correct guess, 0 otherwise).
        """
        correct = func.sum(case((col(Score.base_score) > 0, 1), else_=0)).label("correct")
        total = func.count(col(Score.id)).label("rounds")
        # SQLModel's mapped columns + labels don't resolve under mypy's select overloads.
        stmt = (
            select(  # type: ignore[call-overload]
                col(Score.user_id),
                col(User.display_name),
                func.sum(Score.total_score).label("total"),
                correct,
                total,
            )
            .join(User, col(User.id) == Score.user_id)
            .where(func.date(Score.scored_at) == for_date)
            .group_by(col(Score.user_id), col(User.display_name))
            .order_by(func.sum(Score.total_score).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            LeaderboardEntry(
                rank=i + 1,
                user_id=user_id,
                display_name=display_name,
                score=int(total_score),
                accuracy=(correct_count or 0) / rounds * 100 if rounds else 0.0,
            )
            for i, (user_id, display_name, total_score, correct_count, rounds) in enumerate(rows)
        ]

    async def get_scores_for_rounds(self, round_ids: list[str]) -> dict[str, Score]:
        """Score rows keyed by round id (missing rounds are absent)."""
        if not round_ids:
            return {}
        stmt = select(Score).where(col(Score.round_id).in_(round_ids))
        rows = (await self.session.execute(stmt)).scalars().all()
        return {row.round_id: row for row in rows}

    async def get_user_rating(self, user_id: str) -> float:
        """Current Detection Rating; the default for unknown users."""
        user = await self.session.get(User, user_id)
        return user.detection_rating if user else DEFAULT_RATING

    async def count_user_rounds(self, user_id: str) -> int:
        """Scored rounds played — drives the ELO K-factor (GDD §6.2)."""
        stmt = select(func.count(col(Score.id))).where(Score.user_id == user_id)
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_streak(self, user_id: str, streak_type: str) -> Streak | None:
        stmt = select(Streak).where(Streak.user_id == user_id, Streak.type == streak_type)
        return (await self.session.execute(stmt)).scalar_one_or_none()

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

    async def get_round_for_entry(self, entry_id: str) -> Round | None:
        """The round an entry belongs to (human or AI side)."""
        stmt = select(Round).where(
            or_(col(Round.human_entry_id) == entry_id, col(Round.ai_entry_id) == entry_id)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_round_accuracies(self) -> dict[str, tuple[int, int]]:
        """(correct, total) scored rounds per user — accuracy = correct / total."""
        session_users = {
            game_session.id: game_session.user_id
            for game_session in (await self.session.execute(select(Session))).scalars().all()
        }
        rows = (
            await self.session.execute(
                select(Round.session_id, Round.reveal_data).where(Round.state == "scored")
            )
        ).all()
        tallies: dict[str, tuple[int, int]] = {}
        for session_id, reveal_data in rows:
            user_id = session_users.get(session_id)
            if user_id is None:
                continue
            correct, total = tallies.get(user_id, (0, 0))
            tallies[user_id] = (correct + int(bool((reveal_data or {}).get("vote_correct"))), total + 1)
        return {user_id: (correct, total) for user_id, (correct, total) in tallies.items()}

    async def update_humanity_score(
        self, entry_id: str, score: float, total_votes: int
    ) -> HumanityScore:
        """Upsert the retroactive humanity score for an entry (Master §13.5)."""
        row = await self.session.get(HumanityScore, entry_id)
        if row is None:
            row = HumanityScore(entry_id=entry_id, humanity_score=score, total_votes=total_votes)
            self.session.add(row)
        else:
            row.humanity_score = score
            row.total_votes = total_votes
        await self._save(row)
        return row

    async def save_snapshot(self, for_date: dt.date, entries: list[LeaderboardEntry]) -> None:
        """Replace the day's snapshot rows with the given ranked entries (idempotent)."""
        existing = (
            await self.session.execute(
                select(LeaderboardSnapshot).where(LeaderboardSnapshot.date == for_date)
            )
        ).scalars().all()
        for row in existing:
            await self.session.delete(row)
        for entry in entries:
            self.session.add(
                LeaderboardSnapshot(
                    date=for_date,
                    user_id=entry.user_id,
                    score=entry.score or 0,
                    rank=entry.rank,
                )
            )
        await self.session.commit()

    async def get_snapshot(self, for_date: dt.date) -> list[LeaderboardEntry]:
        rows = (
            await self.session.execute(
                select(LeaderboardSnapshot, User.display_name)
                .join(User, col(User.id) == LeaderboardSnapshot.user_id)
                .where(LeaderboardSnapshot.date == for_date)
                .order_by(col(LeaderboardSnapshot.rank))
            )
        ).all()
        return [
            LeaderboardEntry(
                rank=row.rank,
                user_id=row.user_id,
                display_name=display_name,
                score=row.score,
            )
            for row, display_name in rows
        ]
