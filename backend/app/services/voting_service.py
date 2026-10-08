"""VotingService: anonymous A/B presentation, vote processing, reveal.

The A/B assignment is seeded from the round id, so presenting the same round
always yields the same letters (the player's screen and the reveal can never
disagree) while different rounds assign differently. Humanity scores are
retroactive: the share of voters who guessed each entry was human.
"""

import random

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.voting import VotingRepository
from app.schemas.voting import RevealResult, VoteResult
from app.services.humanity_scoring import HumanityScoring


class VotingService:
    """Owns A/B assignment, vote recording, and the reveal attribution."""

    def __init__(self, repo: VotingRepository) -> None:
        self.repo = repo
        self.humanity = HumanityScoring()

    async def present_entries(self, round_id: str) -> dict[str, str]:
        """{"A": text, "B": text} for a round, moving it into the voting phase."""
        pair = await self.repo.get_round_entries(round_id)
        if pair is None:
            return {}
        human, ai = pair
        human_letter = self._assignment(round_id)
        entries = {human_letter: human.content, self._other(human_letter): ai.content}
        await self._set_state(round_id, "voting")
        return entries

    async def process_vote(self, round_id: str, user_id: str, vote: str) -> VoteResult:
        """Record the vote and report whether the round can proceed to reveal."""
        rnd = await self.repo.get_round(round_id)
        if rnd is None:
            raise NotFoundError(f"unknown round: {round_id}")
        if rnd.state == "scored":
            raise ConflictError("round already revealed")
        row = await self.repo.create_vote(round_id, user_id, vote)
        if row is None:  # pragma: no cover — get_round already proved it exists
            raise NotFoundError(f"unknown round: {round_id}")
        votes = await self.repo.get_votes_for_round(round_id)
        return VoteResult(
            round_id=round_id,
            vote=vote,
            can_reveal=True,
            total_votes=len(votes),
        )

    async def reveal(self, round_id: str) -> RevealResult:
        """Attribute both entries, score humanity, and persist the reveal."""
        rnd = await self.repo.get_round(round_id)
        if rnd is None:
            raise NotFoundError(f"unknown round: {round_id}")
        if rnd.state == "scored":
            raise ConflictError("round already revealed")
        pair = await self.repo.get_round_entries(round_id)
        if pair is None:
            raise ConflictError("round has no entries to reveal")
        human, ai = pair

        human_letter = self._assignment(round_id)
        ai_letter = self._other(human_letter)
        entries = {human_letter: human.content, ai_letter: ai.content}
        votes = await self.repo.get_votes_for_round(round_id)
        humanity_human, humanity_ai = self.humanity.score_round(votes, human_letter, ai_letter)
        vote_correct = rnd.vote is not None and rnd.vote == ai_letter
        explanation = self._explain(ai_letter, rnd.vote, vote_correct, humanity_human, humanity_ai)

        await self.repo.update_humanity_score(human.id, humanity_human, len(votes))
        await self.repo.update_humanity_score(ai.id, humanity_ai, len(votes))
        await self.repo.record_reveal(
            round_id,
            human_letter,
            {
                "vote": rnd.vote,
                "vote_correct": vote_correct,
                "humanity_human": humanity_human,
                "humanity_ai": humanity_ai,
                "explanation": explanation,
                "total_votes": len(votes),
            },
        )

        return RevealResult(
            round_id=round_id,
            entries=entries,
            human_was=human_letter,
            ai_was=ai_letter,
            vote=rnd.vote,
            vote_correct=vote_correct,
            humanity_human=humanity_human,
            humanity_ai=humanity_ai,
            explanation=explanation,
        )

    # ---------------------------------------------------------------------------
    # Internals

    def _assignment(self, round_id: str) -> str:
        """Which letter the human entry gets (stable per round, varies across rounds)."""
        rng = random.Random(f"ab-assignment:{round_id}")
        return "A" if rng.random() < 0.5 else "B"

    @staticmethod
    def _other(letter: str) -> str:
        return "B" if letter == "A" else "A"

    async def _set_state(self, round_id: str, state: str) -> None:
        rnd = await self.repo.get_round(round_id)
        if rnd is not None:
            rnd.state = state
            await self.repo.session.commit()

    @staticmethod
    def _explain(
        ai_letter: str, vote: str | None, vote_correct: bool, humanity_human: float, humanity_ai: float
    ) -> str:
        scores = f"Humanity: your entry {humanity_human:.0f}, AI entry {humanity_ai:.0f}."
        if vote is None:
            return f"Entry {ai_letter} was the AI. {scores}"
        if vote_correct:
            return f"Entry {ai_letter} was the AI — nice catch. {scores}"
        return f"Entry {ai_letter} was the AI and it fooled you. {scores}"
