"""Scoring engine: round score per Master Architecture §12.5.

Formula: guess_bonus (base when the vote is correct) + time_bonus + streak_bonus.
The time bonus is capped at half the base score — for the catalog's base of 100
this equals §12.5's literal min(50, ...) cap while generalizing to other bases.

`calculate_breakdown` (Sprint 12) exposes the components for persistence;
`calculate_score` remains the integer total.
"""

from app.schemas.challenge import ChallengeDefinition
from app.schemas.scoring import RoundScore


class ScoringEngine:
    def calculate_breakdown(
        self,
        vote_correct: bool,
        time_remaining: float,
        time_limit: float,
        streak: int,
        challenge: ChallengeDefinition,
    ) -> RoundScore:
        rules = challenge.scoring_rules
        ratio = 0.0
        if time_limit > 0:
            ratio = max(0.0, min(1.0, time_remaining / time_limit))
        time_bonus = int(min(rules.base_score * 0.5, rules.base_score * rules.time_bonus_multiplier * ratio))
        streak_bonus = int(max(0, streak) * rules.base_score * rules.streak_multiplier)
        base = rules.base_score if vote_correct else 0
        return RoundScore(
            vote_correct=vote_correct,
            base=base,
            time_bonus=time_bonus,
            streak_bonus=streak_bonus,
            total=base + time_bonus + streak_bonus,
        )

    def calculate_score(
        self,
        vote_correct: bool,
        time_remaining: float,
        time_limit: float,
        streak: int,
        challenge: ChallengeDefinition,
    ) -> int:
        return self.calculate_breakdown(
            vote_correct, time_remaining, time_limit, streak, challenge
        ).total
