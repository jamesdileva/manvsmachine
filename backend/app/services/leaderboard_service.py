"""LeaderboardService: daily/all-time boards and daily snapshots (GDD §6.4)."""

import datetime as dt

from app.repositories.scoring import ScoringRepository
from app.repositories.user import UserRepository
from app.schemas.leaderboard import DailyLeaderboardResponse, LeaderboardEntry


class LeaderboardService:
    """Ranked views over scores and ratings; persists end-of-day snapshots."""

    def __init__(self, repo: ScoringRepository, user_repo: UserRepository) -> None:
        self.repo = repo
        self.user_repo = user_repo

    async def get_daily_leaderboard(
        self, for_date: dt.date, limit: int = 100
    ) -> list[LeaderboardEntry]:
        """Users ranked by total score earned on `for_date` (with accuracy)."""
        return await self.repo.get_daily_scores(for_date, limit)

    async def get_daily_leaderboard_response(
        self, for_date: dt.date, limit: int = 100
    ) -> DailyLeaderboardResponse:
        return DailyLeaderboardResponse(
            date=for_date, entries=await self.get_daily_leaderboard(for_date, limit)
        )

    async def get_all_time_leaderboard(self, limit: int = 100) -> list[LeaderboardEntry]:
        """Users ranked by Detection Rating, with overall vote accuracy."""
        entries = await self.user_repo.get_leaderboard(limit)
        accuracies = await self.repo.get_round_accuracies()
        return [
            entry.model_copy(
                update={"accuracy": self._accuracy(accuracies.get(entry.user_id))}
            )
            for entry in entries
        ]

    async def generate_snapshot(self, for_date: dt.date) -> list[LeaderboardEntry]:
        """Persist the day's daily leaderboard as an immutable snapshot."""
        entries = await self.get_daily_leaderboard(for_date)
        await self.repo.save_snapshot(for_date, entries)
        return entries

    @staticmethod
    def _accuracy(tally: tuple[int, int] | None) -> float:
        if not tally or not tally[1]:
            return 0.0
        correct, total = tally
        return correct / total * 100
