"""Scoring schemas: the per-round score breakdown."""

from pydantic import BaseModel


class RoundScore(BaseModel):
    """A round's score components (Master Architecture §12.5).

    `base` is the guess component (100 on a correct detection, 0 otherwise);
    time and streak bonuses apply regardless, per the §12.5 formula.
    """

    vote_correct: bool
    base: int
    time_bonus: int
    streak_bonus: int
    total: int
