"""SessionService: the round state machine and session orchestration.

Round lifecycle (Master §12.1/§14): WRITING -> REVEAL_AI -> VOTING -> SCORED,
with the session completing after its final round. This is the composition root
for a round: challenge assignment, human + AI entries, anonymized presentation,
vote + reveal, score + rating + streaks, and the session summary.

A round's DB state maps the Master states as: writing=WRITING,
reveal_ai=entries generated, voting=anonymized A/B waiting for the vote,
scored=terminal (SCORE + RESULT: the score is recorded and the round closed).
"""

import random

from app.core.exceptions import ConflictError, ConstraintViolationError, NotFoundError
from app.db.models import Round, Session, utc_now
from app.repositories.session import SessionRepository
from app.schemas.session import (
    ChallengeBrief,
    RoundResult,
    RoundState,
    RoundSubmission,
    RoundSummary,
    SessionSummary,
)
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.scoring_service import STREAK_CORRECT, STREAK_DAILY, ScoringService
from app.services.voting_service import VotingService

SESSION_ROUNDS = 3

# Allowed round-state transitions; anything else is rejected (sprint acceptance).
ROUND_TRANSITIONS: dict[str, set[str]] = {
    "writing": {"reveal_ai"},
    "reveal_ai": {"voting"},
    "voting": {"scored"},
    "scored": set(),
}


class SessionService:
    """Owns the round lifecycle and composes the challenge/AI/voting/scoring services."""

    def __init__(
        self,
        session_repo: SessionRepository,
        challenge_service: ChallengeService,
        ai_service: AIService,
        voting_service: VotingService,
        scoring_service: ScoringService,
    ) -> None:
        self.repo = session_repo
        self.challenges = challenge_service
        self.ai = ai_service
        self.voting = voting_service
        self.scoring = scoring_service

    # ---------------------------------------------------------------------------
    # Sessions

    async def start_session(
        self, user_id: str, session_type: str, challenge_ids: list[str] | None = None
    ) -> Session:
        """Create a session (daily = today's rotation pool; practice = explicit or random)."""
        if session_type == "daily":
            ids = self.challenges.get_daily_session_pool(utc_now().date())
        elif challenge_ids:
            for challenge_id in challenge_ids:
                try:
                    self.challenges.get_challenge(challenge_id)
                except KeyError as exc:
                    raise NotFoundError(f"unknown challenge: {challenge_id}") from exc
            ids = challenge_ids[:SESSION_ROUNDS]
        else:
            pool = self.challenges.get_challenge_pool()
            ids = random.sample(pool, min(SESSION_ROUNDS, len(pool)))
        return await self.repo.create(user_id, ids, is_daily=session_type == "daily")

    async def start_next_round(self, session_id: str, user_id: str) -> RoundState | None:
        """The round to play next; None (and a stamped session) once all rounds are done."""
        game_session = await self._owned_session(session_id, user_id)
        rounds = await self.repo.get_rounds_for_session(session_id)
        if game_session.rounds_played >= len(game_session.challenge_ids):
            if game_session.completed_at is None:
                await self.repo.complete(session_id, await self._total_score(rounds))
            return None
        next_number = game_session.rounds_played + 1
        rnd = next((r for r in rounds if r.round_number == next_number), None)
        if rnd is None:
            rnd = await self.repo.create_round(
                session_id, game_session.challenge_ids[next_number - 1], next_number
            )
        return self._round_state(rnd, game_session)

    async def get_session_summary(self, session_id: str, user_id: str) -> SessionSummary:
        """Totals, accuracy, and the per-round breakdown for a session."""
        game_session = await self._owned_session(session_id, user_id)
        rounds = await self.repo.get_rounds_for_session(session_id)
        scores = await self.scoring.repo.get_scores_for_rounds([r.id for r in rounds])

        scored = [r for r in rounds if r.state == "scored"]
        correct = sum(1 for r in scored if (r.reveal_data or {}).get("vote_correct"))
        accuracy = correct / len(scored) * 100 if scored else None
        streak = await self.scoring.get_current_streak(user_id, STREAK_CORRECT)
        return SessionSummary(
            session_id=session_id,
            type="daily" if game_session.is_daily else "practice",
            rounds_total=len(game_session.challenge_ids),
            rounds_played=game_session.rounds_played,
            total_score=sum(score.total_score for score in scores.values()),
            accuracy=accuracy,
            rounds=[
                RoundSummary(
                    round_number=r.round_number,
                    challenge_id=r.challenge_id,
                    vote=r.vote,
                    correct=(r.reveal_data or {}).get("vote_correct"),
                    score=scores[r.id].total_score if r.id in scores else None,
                    humanity_human=self._humanity((r.reveal_data or {}).get("humanity_human")),
                    humanity_ai=self._humanity((r.reveal_data or {}).get("humanity_ai")),
                )
                for r in sorted(rounds, key=lambda r: r.round_number)
                if r.state == "scored"  # results only; an in-progress round is not a result
            ],
            rating_change=None,  # needs a session-start rating snapshot (not in the MVP schema)
            streak=streak,
        )

    # ---------------------------------------------------------------------------
    # Round lifecycle

    async def submit_entry(self, round_id: str, entry: str, user_id: str) -> RoundSubmission:
        """Store the human entry, generate the AI entry, and present both as A/B."""
        rnd = await self._owned_round(round_id, user_id)
        if rnd.state != "writing":
            raise ConflictError(f"round is not accepting entries (state: {rnd.state})")
        challenge = self.challenges.get_challenge(rnd.challenge_id)

        input_result = self.challenges.validate_input(entry, challenge.input_type)
        if not input_result.valid:
            raise ConstraintViolationError(input_result.errors)
        constraints = self.challenges.apply_constraints(entry, challenge)
        if not constraints.valid:
            raise ConstraintViolationError(constraints.hard_violations)

        time_spent = max(0.0, (utc_now() - rnd.started_at).total_seconds())
        human = await self.repo.create_entry(
            round_id,
            "human",
            entry,
            validity={"input_valid": True},
            constraint_violations=constraints.soft_violations,
        )
        # ProviderError (chain exhausted) propagates; the endpoint maps it to 503.
        ai_text = await self.ai.generate_entry(challenge)
        ai = await self.repo.create_entry(round_id, "ai", ai_text)

        rnd.human_entry_id = human.id
        rnd.ai_entry_id = ai.id
        rnd.time_spent_seconds = time_spent
        await self.repo.save_round(rnd)

        await self.transition_round(round_id, "reveal_ai")
        entries = await self.voting.present_entries(round_id)
        provider = self.ai.active_provider
        return RoundSubmission(
            round_id=round_id,
            entries=entries,
            ai_provider=provider.get_provider_name() if provider else "",
            ai_model=provider.get_model_name() if provider else "",
            hard_violations=[],
            soft_violations=constraints.soft_violations,
        )

    async def vote(self, round_id: str, user_id: str, vote: str) -> RoundResult:
        """Record the vote, reveal, score the round, and update rating + streaks."""
        rnd = await self._owned_round(round_id, user_id)
        if rnd.state == "scored":
            raise ConflictError("round already revealed")
        if rnd.state != "voting":
            raise ConflictError(f"round is not accepting votes (state: {rnd.state})")
        game_session = await self._owned_session(rnd.session_id, user_id)
        challenge = self.challenges.get_challenge(rnd.challenge_id)

        await self.voting.process_vote(round_id, user_id, vote)
        reveal = await self.voting.reveal(round_id)

        time_spent = rnd.time_spent_seconds or 0.0
        time_remaining = max(0.0, challenge.time_limit_seconds - time_spent)
        streak_before = await self.scoring.get_current_streak(user_id, STREAK_CORRECT)
        score = self.scoring.calculate_round_score(
            reveal.vote_correct, time_remaining, challenge.time_limit_seconds, streak_before, challenge
        )
        await self.scoring.repo.create_score(
            user_id, round_id, score.base, score.time_bonus, score.streak_bonus, score.total
        )
        rating = await self.scoring.update_detection_rating(
            user_id, reveal.vote_correct, reveal.humanity_ai
        )
        streak_after = await self.scoring.update_streak(
            user_id, STREAK_CORRECT, reveal.vote_correct
        )
        if game_session.is_daily:
            await self.scoring.update_streak(user_id, STREAK_DAILY, True)

        await self.complete_round(round_id)  # stamps completed_at + advances the session
        return RoundResult(
            round_id=round_id,
            reveal=reveal,
            score=score,
            rating=rating,
            streak=streak_after,
        )

    async def complete_round(self, round_id: str) -> RoundSummary:
        """Stamp the round complete and advance the session's played counter."""
        rnd = await self.repo.get_round(round_id)
        if rnd is None:
            raise NotFoundError(f"unknown round: {round_id}")
        if rnd.state != "scored":
            raise ConflictError("round is not complete yet")
        if rnd.completed_at is None:
            rnd.completed_at = utc_now()
            await self.repo.save_round(rnd)
            await self.repo.increment_rounds_played(rnd.session_id)
        score = (await self.scoring.repo.get_scores_for_rounds([round_id])).get(round_id)
        return RoundSummary(
            round_number=rnd.round_number,
            challenge_id=rnd.challenge_id,
            vote=rnd.vote,
            correct=(rnd.reveal_data or {}).get("vote_correct"),
            score=score.total_score if score else None,
            humanity_human=self._humanity((rnd.reveal_data or {}).get("humanity_human")),
            humanity_ai=self._humanity((rnd.reveal_data or {}).get("humanity_ai")),
        )

    # ---------------------------------------------------------------------------
    # State machine

    async def get_round_state(self, round_id: str) -> str:
        rnd = await self.repo.get_round(round_id)
        return rnd.state if rnd is not None else ""

    async def transition_round(self, round_id: str, target_state: str) -> bool:
        """Move a round to a new state; False (and no change) for invalid transitions."""
        if target_state not in ROUND_TRANSITIONS:
            return False
        rnd = await self.repo.get_round(round_id)
        if rnd is None:
            return False
        if target_state not in ROUND_TRANSITIONS[rnd.state]:
            return False
        rnd.state = target_state
        await self.repo.save_round(rnd)
        return True

    # ---------------------------------------------------------------------------
    # Internals

    def _round_state(self, rnd: Round, game_session: Session) -> RoundState:
        challenge = self.challenges.get_challenge(rnd.challenge_id)
        return RoundState(
            round_id=rnd.id,
            challenge=ChallengeBrief(
                id=challenge.id,
                prompt=challenge.prompt,
                time_limit_seconds=challenge.time_limit_seconds,
            ),
            round_number=rnd.round_number,
            rounds_total=len(game_session.challenge_ids),
            state=rnd.state,
        )

    async def _owned_session(self, session_id: str, user_id: str) -> Session:
        game_session = await self.repo.get(session_id)
        if game_session is None or game_session.user_id != user_id:
            raise NotFoundError("session not found")
        return game_session

    async def _owned_round(self, round_id: str, user_id: str) -> Round:
        rnd = await self.repo.get_round(round_id)
        if rnd is None:
            raise NotFoundError(f"unknown round: {round_id}")
        await self._owned_session(rnd.session_id, user_id)
        return rnd

    async def _total_score(self, rounds: list[Round]) -> int:
        scores = await self.scoring.repo.get_scores_for_rounds([r.id for r in rounds])
        return sum(score.total_score for score in scores.values())

    @staticmethod
    def _humanity(value: float | None) -> int | None:
        return None if value is None else int(value)
