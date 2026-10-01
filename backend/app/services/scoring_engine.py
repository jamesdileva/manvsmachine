"""Scoring engine: round score per Master Architecture §12.5.

Formula: guess_bonus (base when the vote is correct) + time_bonus + streak_bonus.
The time bonus is capped at half the base score — for the catalog's base of 100
this equals §12.5's literal min(50, ...) cap while generalizing to other bases.
"""

from app.schemas.challenge import ChallengeDefinition


class ScoringEngine:
    def calculate_score(
        self,
        vote_correct: bool,
        time_remaining: float,
        time_limit: float,
        streak: int,
        challenge: ChallengeDefinition,
    ) -> int:
        rules = challenge.scoring_rules
        ratio = 0.0
        if time_limit > 0:
            ratio = max(0.0, min(1.0, time_remaining / time_limit))
        time_bonus = min(rules.base_score * 0.5, rules.base_score * rules.time_bonus_multiplier * ratio)
        streak_bonus = max(0, streak) * rules.base_score * rules.streak_multiplier
        guess_bonus = rules.base_score if vote_correct else 0
        return int(guess_bonus + time_bonus + streak_bonus)
