"""ProfileService: player stats and display-name updates (Implementation Guide §2.5)."""

from app.core.exceptions import NotFoundError
from app.repositories.scoring import ScoringRepository
from app.repositories.user import UserRepository
from app.schemas.user import ProfileResponse
from app.services.scoring_service import STREAK_CORRECT, STREAK_DAILY


class ProfileService:
    """Aggregates a player's rating, rounds, accuracy, streaks, and humanity trend."""

    def __init__(self, repo: ScoringRepository, user_repo: UserRepository) -> None:
        self.repo = repo
        self.user_repo = user_repo

    async def get_profile(self, user_id: str) -> ProfileResponse:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("user not found")
        accuracies = await self.repo.get_round_accuracies()
        return ProfileResponse(
            user_id=user.id,
            display_name=user.display_name,
            is_guest=user.password_hash is None,
            detection_rating=user.detection_rating,
            total_rounds=await self.repo.count_user_rounds(user_id),
            overall_accuracy=self._accuracy(accuracies.get(user.id)),
            current_streak=await self._streak_count(user.id, STREAK_CORRECT),
            longest_streak=self._longest_record(await self.repo.get_streak(user.id, STREAK_CORRECT)),
            daily_challenge_streak=await self._daily_streak(user.id),
            recent_humanity_scores=await self.repo.get_recent_humanity_scores(user.id),
        )

    async def update_display_name(self, user_id: str, display_name: str) -> ProfileResponse:
        """Rename the player and return the refreshed profile."""
        updated = await self.user_repo.update_display_name(user_id, display_name)
        if updated is None:
            raise NotFoundError("user not found")
        return await self.get_profile(user_id)

    async def _streak_count(self, user_id: str, streak_type: str) -> int:
        streak = await self.repo.get_streak(user_id, streak_type)
        return streak.count if streak else 0

    async def _daily_streak(self, user_id: str) -> int:
        streak = await self.repo.get_streak(user_id, STREAK_DAILY)
        return streak.count if streak else 0

    @staticmethod
    def _longest_record(streak: object) -> int:
        return getattr(streak, "longest_record", 0) or 0

    @staticmethod
    def _accuracy(tally: tuple[int, int] | None) -> float:
        if not tally or not tally[1]:
            return 0.0
        correct, total = tally
        return correct / total * 100
