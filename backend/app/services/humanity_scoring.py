"""Humanity scoring: retroactive 0-100 score from player guesses (Master §13.5).

Humanity = percentage of voters who guessed the entry was human. An AI entry
that fooled voters scores high; a human entry that read as machine scores low.
Score feeds challenge balancing and the player's humanity trend.
"""

from app.db.models import Vote


class HumanityScoring:
    """Computes per-entry humanity from the votes on a round."""

    def calculate(self, votes: list[Vote], entry_letter: str) -> float:
        """Share of voters who picked the OTHER entry as the AI (0-100).

        `entry_letter` is the entry's A/B label in the round being scored.
        No votes means no evidence of humanity, so the score is 0.
        """
        if not votes:
            return 0.0
        guessed_human = sum(1 for vote in votes if vote.selected_entry != entry_letter)
        return guessed_human / len(votes) * 100

    def score_round(self, votes: list[Vote], human_letter: str, ai_letter: str) -> tuple[float, float]:
        """(humanity_human, humanity_ai) for one round."""
        return (
            self.calculate(votes, human_letter),
            self.calculate(votes, ai_letter),
        )
