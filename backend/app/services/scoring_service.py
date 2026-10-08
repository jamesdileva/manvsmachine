"""ScoringService: round scores, Detection Rating (ELO), humanity, streaks.

Rating math follows GDD §6.2: expected = 1 / (1 + 10^((AI_rating - player) / 400)),
change = K x (actual - expected), K = 32 for players with fewer than 50 scored
rounds and 16 after. The AI's rating is derived from its entry's humanity score
(50 = parity with a 1000-rated player; the span keeps expected within a sane band).
"""

import datetime as dt

from app.db.models import Streak, Vote, utc_now
from app.repositories.scoring import ScoringRepository
from app.repositories.user import UserRepository
from app.schemas.challenge import ChallengeDefinition
from app.schemas.scoring import RoundScore
from app.services.humanity_scoring import HumanityScoring
from app.services.scoring_engine import ScoringEngine

STREAK_CORRECT = "correct_guess"
STREAK_DAILY = "daily_challenge"

NEW_PLAYER_ROUNDS = 50
NEW_PLAYER_K = 32.0
ESTABLISHED_K = 16.0
HUMANITY_PARITY = 50.0  # humanity score that maps to a 1000 AI rating
HUMANITY_RATING_SPAN = 4.0  # rating points per humanity point above/below parity
RATING_FLOOR = 100.0


class ScoringService:
    """Round scoring, rating updates, humanity recomputation, and streaks."""

    def __init__(self, repo: ScoringRepository, user_repo: UserRepository) -> None:
        self.repo = repo
        self.user_repo = user_repo
        self.engine = ScoringEngine()
        self.humanity = HumanityScoring()

    # ---------------------------------------------------------------------------
    # Round score

    def calculate_round_score(
        self,
        vote_correct: bool,
        time_remaining: float,
        time_limit: float,
        streak: int,
        challenge: ChallengeDefinition,
    ) -> RoundScore:
        """The §12.5 breakdown: guess base + time bonus + streak bonus."""
        return self.engine.calculate_breakdown(
            vote_correct, time_remaining, time_limit, streak, challenge
        )

    # ---------------------------------------------------------------------------
    # Detection Rating (ELO)

    def calculate_rating_change(
        self,
        player_rating: float,
        ai_humanity_score: float,
        vote_correct: bool,
        k: float = NEW_PLAYER_K,
    ) -> float:
        """Signed rating delta for one round (GDD §6.2)."""
        ai_rating = 1000.0 + (ai_humanity_score - HUMANITY_PARITY) * HUMANITY_RATING_SPAN
        expected = 1.0 / (1.0 + 10.0 ** ((ai_rating - player_rating) / 400.0))
        actual = 1.0 if vote_correct else 0.0
        return k * (actual - expected)

    async def update_detection_rating(
        self, user_id: str, vote_correct: bool, ai_humanity_score: float
    ) -> float:
        """Apply one round's ELO change; returns the player's new rating."""
        rating = await self.repo.get_user_rating(user_id)
        rounds_played = await self.repo.count_user_rounds(user_id)
        k = NEW_PLAYER_K if rounds_played < NEW_PLAYER_ROUNDS else ESTABLISHED_K
        change = self.calculate_rating_change(rating, ai_humanity_score, vote_correct, k)
        new_rating = max(RATING_FLOOR, round(rating + change, 1))
        await self.user_repo.update_rating(user_id, new_rating)
        return new_rating

    # ---------------------------------------------------------------------------
    # Humanity score

    async def update_humanity_score(
        self, entry_id: str, votes: list[Vote], is_ai: bool
    ) -> float:
        """Recompute and persist an entry's retroactive humanity (Master §13.5).

        The entry's A/B letter comes from the round's reveal (`human_was`);
        before a reveal there is no letter, so the score is 0 and nothing is stored.
        """
        letter = await self._entry_letter(entry_id, is_ai)
        if letter is None:
            return 0.0
        score = self.humanity.calculate(votes, letter)
        await self.repo.update_humanity_score(entry_id, score, len(votes))
        return score

    async def _entry_letter(self, entry_id: str, is_ai: bool) -> str | None:
        rnd = await self.repo.get_round_for_entry(entry_id)
        if rnd is None:
            return None
        human_was = (rnd.reveal_data or {}).get("human_was")
        if human_was not in ("A", "B"):
            return None
        if is_ai:
            return "B" if human_was == "A" else "A"
        return human_was

    # ---------------------------------------------------------------------------
    # Streaks

    async def update_streak(self, user_id: str, streak_type: str, correct: bool) -> int:
        """Advance or reset a streak; returns the new count.

        `correct_guess`: each correct guess extends, a wrong guess resets.
        `daily_challenge`: consecutive days extend, a gap of more than a day resets,
        and replaying the same day keeps the count.
        """
        streak = await self.repo.get_streak(user_id, streak_type)
        if streak_type == STREAK_DAILY:
            count = self._next_daily_count(streak, correct)
        else:
            count = (streak.count + 1) if (correct and streak is not None) else (1 if correct else 0)
        row = await self.repo.update_streak(user_id, streak_type, count)
        return row.count

    async def get_current_streak(self, user_id: str, streak_type: str) -> int:
        """The stored count; a daily streak idle for more than a day reads as 0."""
        streak = await self.repo.get_streak(user_id, streak_type)
        if streak is None:
            return 0
        if streak_type == STREAK_DAILY and streak.last_active_date < utc_now().date() - dt.timedelta(days=1):
            return 0
        return streak.count

    @staticmethod
    def _next_daily_count(streak: Streak | None, played_today: bool) -> int:
        today = utc_now().date()
        if not played_today:
            return 0
        if streak is None:
            return 1
        if streak.last_active_date == today:
            return streak.count
        if streak.last_active_date == today - dt.timedelta(days=1):
            return streak.count + 1
        return 1
