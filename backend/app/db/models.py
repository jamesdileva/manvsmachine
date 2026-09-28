"""SQLModel table definitions for the full MVP schema.

Source: docs/02_Implementation_Guide.md §1.1 (models) and §1.2 (indexes).
SQLite via aiosqlite; JSON columns use SQLAlchemy's generic JSON type;
table names are explicit and plural per the architecture's naming conventions.
The `datetime` module is imported as `dt` so fields named `date` can be
annotated `dt.date` (pydantic rejects `date: date` as a name/annotation clash).
"""

import datetime as dt
import uuid

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, SQLModel


def utc_now() -> dt.datetime:
    """Timezone-aware UTC now (datetime.utcnow is deprecated since 3.12)."""
    return dt.datetime.now(dt.UTC)


def gen_uuid() -> str:
    """String UUID primary key generator."""
    return str(uuid.uuid4())


class User(SQLModel, table=True):
    """A player — guest or registered."""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_guest_id", "guest_id"),
        Index("idx_users_detection_rating", "detection_rating"),
    )

    id: str = Field(default_factory=gen_uuid, primary_key=True)
    guest_id: str | None = Field(default=None, unique=True)
    display_name: str
    email: str | None = None
    password_hash: str | None = None  # set for registered accounts; guests stay None
    detection_rating: float = Field(default=1000.0)
    created_at: dt.datetime = Field(default_factory=utc_now)
    updated_at: dt.datetime = Field(default_factory=utc_now)


class Challenge(SQLModel, table=True):
    """A micro-challenge definition (mirrors the JSON library, loaded by Sprint 26)."""

    __tablename__ = "challenges"

    id: str = Field(primary_key=True)  # e.g. "challenge_slogan_01"
    name: str
    interaction_type: str = "Quick Text"
    prompt: str
    constraints: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    time_limit_seconds: int = 20
    input_type: str = "text_single_line"
    voting_criteria: str = "most_believable"
    difficulty: int = 2  # 1-5
    scoring_rules: dict = Field(default_factory=dict, sa_column=Column(JSON))
    ai_prompt_template_id: str
    replayability: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: dt.datetime = Field(default_factory=utc_now)
    updated_at: dt.datetime = Field(default_factory=utc_now)


class ChallengeDaily(SQLModel, table=True):
    """Deterministic daily challenge assignment by date."""

    __tablename__ = "challenge_daily"

    date: dt.date = Field(primary_key=True)
    challenge_id: str = Field(foreign_key="challenges.id")
    variant_constraints: list[dict] | None = Field(default=None, sa_column=Column(JSON))


class Session(SQLModel, table=True):
    """A play session: 3 rounds (daily or practice)."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_started_at", "started_at"),
    )

    id: str = Field(default_factory=gen_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    challenge_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    started_at: dt.datetime = Field(default_factory=utc_now)
    completed_at: dt.datetime | None = None
    final_score: int | None = None
    rounds_played: int = 0
    is_daily: bool = False


class Round(SQLModel, table=True):
    """One challenge round within a session; the round state machine lives here."""

    __tablename__ = "rounds"
    __table_args__ = (
        Index("idx_rounds_session_id", "session_id"),
        Index("idx_rounds_challenge_id", "challenge_id"),
        Index("idx_rounds_state", "state"),
    )

    id: str = Field(default_factory=gen_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id")
    challenge_id: str = Field(foreign_key="challenges.id")
    round_number: int
    human_entry_id: str | None = None
    ai_entry_id: str | None = None
    vote: str | None = None  # "A" or "B" (which entry the player chose as AI)
    reveal_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    state: str = "writing"  # writing, reveal_ai, voting, scored
    started_at: dt.datetime = Field(default_factory=utc_now)
    completed_at: dt.datetime | None = None
    time_spent_seconds: float | None = None


class Entry(SQLModel, table=True):
    """An answer submitted for a round — human or AI."""

    __tablename__ = "entries"
    __table_args__ = (
        Index("idx_entries_round_id", "round_id"),
        Index("idx_entries_author_type", "author_type"),
    )

    id: str = Field(default_factory=gen_uuid, primary_key=True)
    round_id: str = Field(foreign_key="rounds.id")
    author_type: str  # "human" or "ai"
    content: str
    submitted_at: dt.datetime = Field(default_factory=utc_now)
    validity: dict = Field(default_factory=dict, sa_column=Column(JSON))
    constraint_violations: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class AIEntry(SQLModel, table=True):
    """Provider metadata for AI-generated entries (audit/reproducibility)."""

    __tablename__ = "ai_entries"

    entry_id: str = Field(foreign_key="entries.id", primary_key=True)
    provider: str  # "openai", "anthropic", "stub"
    model: str
    prompt_version: str
    prompt_hash: str
    raw_response: str
    sanitized_response: str
    token_count: int | None = None
    generated_at: dt.datetime = Field(default_factory=utc_now)


class Vote(SQLModel, table=True):
    """The player's guess: which anonymized entry (A/B) was the AI's."""

    __tablename__ = "votes"
    __table_args__ = (
        Index("idx_votes_round_id", "round_id"),
        Index("idx_votes_user_id", "user_id"),
    )

    id: str = Field(default_factory=gen_uuid, primary_key=True)
    round_id: str = Field(foreign_key="rounds.id")
    user_id: str = Field(foreign_key="users.id")
    selected_entry: str  # "A" or "B"
    voted_at: dt.datetime = Field(default_factory=utc_now)


class Score(SQLModel, table=True):
    """Per-round score breakdown for a player."""

    __tablename__ = "scores"
    __table_args__ = (
        Index("idx_scores_user_id", "user_id"),
        Index("idx_scores_scored_at", "scored_at"),
    )

    id: str = Field(default_factory=gen_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    round_id: str = Field(foreign_key="rounds.id")
    base_score: int
    time_bonus: int
    streak_bonus: int
    total_score: int
    scored_at: dt.datetime = Field(default_factory=utc_now)


class HumanityScore(SQLModel, table=True):
    """How human-like an entry appears (0-100), aggregated over votes."""

    __tablename__ = "humanity_scores"
    __table_args__ = (Index("idx_humanity_scores_last_updated", "last_updated"),)

    entry_id: str = Field(foreign_key="entries.id", primary_key=True)
    humanity_score: float  # 0.0 - 100.0
    total_votes: int = 0
    last_updated: dt.datetime = Field(default_factory=utc_now)


class Streak(SQLModel, table=True):
    """Streak counters per user (daily challenge, correct guesses)."""

    __tablename__ = "streaks"
    __table_args__ = (Index("idx_streaks_user_type", "user_id", "type"),)

    id: str = Field(default_factory=gen_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    type: str = "daily_challenge"  # "daily_challenge", "correct_guess"
    count: int = 0
    last_active_date: dt.date = Field(default_factory=lambda: utc_now().date())
    longest_record: int = 0


class LeaderboardSnapshot(SQLModel, table=True):
    """Daily leaderboard snapshot: rank per user per date."""

    __tablename__ = "leaderboard_snapshots"
    __table_args__ = (Index("idx_leaderboard_date", "date"),)

    date: dt.date = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    score: int
    rank: int


class PromptAudit(SQLModel, table=True):
    """Versioned audit trail: every AI prompt + response used in a round."""

    __tablename__ = "prompt_audit"
    __table_args__ = (
        Index("idx_prompt_audit_recorded_at", "recorded_at"),
        Index("idx_prompt_audit_challenge_id", "challenge_id"),
    )

    id: str = Field(default_factory=gen_uuid, primary_key=True)
    prompt_version: str
    prompt_system: str
    prompt_user: str
    challenge_id: str = Field(foreign_key="challenges.id")
    ai_response: str  # sanitized
    raw_response: str  # original, for debugging
    provider: str  # "openai", "anthropic", "stub"
    model: str
    token_count: int | None = None
    recorded_at: dt.datetime = Field(default_factory=utc_now)


__all__ = [
    "AIEntry",
    "Challenge",
    "ChallengeDaily",
    "Entry",
    "HumanityScore",
    "LeaderboardSnapshot",
    "PromptAudit",
    "Round",
    "Score",
    "Session",
    "Streak",
    "User",
    "Vote",
    "gen_uuid",
    "utc_now",
]
