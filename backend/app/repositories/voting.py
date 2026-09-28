"""Voting persistence: votes, anonymized entries, reveal records."""

import random

from sqlmodel import col, select

from app.db.models import Entry, Round, Vote
from app.repositories.base import BaseRepository

VALID_VOTES = {"A", "B"}


class VotingRepository(BaseRepository):
    async def create_vote(self, round_id: str, user_id: str, vote: str) -> Vote | None:
        """Record a vote and denormalize it onto the round. None if round missing."""
        if vote not in VALID_VOTES:
            raise ValueError(f"invalid vote: {vote!r} (expected 'A' or 'B')")
        rnd = await self.session.get(Round, round_id)
        if rnd is None:
            return None
        vote_row = Vote(round_id=round_id, user_id=user_id, selected_entry=vote)
        self.session.add(vote_row)
        rnd.vote = vote
        await self.session.commit()
        return vote_row

    async def get_votes_for_round(self, round_id: str) -> list[Vote]:
        stmt = select(Vote).where(Vote.round_id == round_id).order_by(col(Vote.voted_at))
        return list((await self.session.execute(stmt)).scalars().all())

    async def record_reveal(
        self, round_id: str, human_was: str, reveal_data: dict | None = None
    ) -> Round | None:
        """Merge attribution into reveal_data and mark the round scored."""
        if human_was not in VALID_VOTES:
            raise ValueError(f"invalid human_was: {human_was!r} (expected 'A' or 'B')")
        rnd = await self.session.get(Round, round_id)
        if rnd is None:
            return None
        rnd.reveal_data = {**(reveal_data or {}), "human_was": human_was}
        rnd.state = "scored"
        await self.session.commit()
        return rnd

    async def get_entries_anonymized(
        self, round_id: str, rng: random.Random | None = None
    ) -> dict[str, str]:
        """Return {"A": text, "B": text} with randomized A/B assignment ({} if unavailable).

        Pass a seeded `random.Random` for reproducible assignment (VotingService does).
        """
        rnd = await self.session.get(Round, round_id)
        if rnd is None or rnd.human_entry_id is None or rnd.ai_entry_id is None:
            return {}
        human = await self.session.get(Entry, rnd.human_entry_id)
        ai = await self.session.get(Entry, rnd.ai_entry_id)
        if human is None or ai is None:
            return {}
        chooser = rng or random.Random()
        if chooser.random() < 0.5:
            return {"A": human.content, "B": ai.content}
        return {"A": ai.content, "B": human.content}
