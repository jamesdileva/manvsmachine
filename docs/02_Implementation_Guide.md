# Man vs. Machine — Implementation Guide

> **Version:** 1.0
> **Status:** Draft — Sprint 0 (Pre-MVP)
> **Audience:** Developers, AI coding agents
> **Related:** See `docs/01_Master_Architecture.md` for architecture overview and `docs/03_Sprint_Plan.md` for the sprint roadmap.

This document is the **technical reference** for implementing Man vs. Machine. It provides concrete specifications — database schemas, API contracts, service interfaces, WebSocket events, and component hierarchies — that map directly to code. Every sprint in `docs/03_Sprint_Plan.md` references sections from this guide.

---

## Table of Contents

1.  Database Schema
    - 1.1 SQLModel Models
    - 1.2 Indexes
    - 1.3 Migrations (Alembic)
2.  API Endpoints
    - 2.1 Auth
    - 2.2 Challenges
    - 2.3 Session
    - 2.4 Leaderboard
    - 2.5 Profile
    - 2.6 Share
3.  WebSocket API
    - 3.1 Connection
    - 3.2 Events
4.  Repositories
    - 4.1 UserRepository
    - 4.2 ChallengeRepository
    - 4.3 SessionRepository
    - 4.4 VotingRepository
    - 4.5 ScoringRepository
    - 4.6 PromptAuditRepository
5.  Services
    - 5.1 ChallengeService
    - 5.2 AIService
    - 5.3 VotingService
    - 5.4 ScoringService
    - 5.5 SessionService
    - 5.6 ContentFilter
    - 5.7 PromptAuditService
    - 5.8 ShareService
6.  AI Provider Integration
    - 6.1 Provider Interface
    - 6.2 OpenAIProvider
    - 6.3 AnthropicProvider
    - 6.4 StubProvider
    - 6.5 Provider Selection Logic
7.  Frontend State Management
    - 7.1 React Contexts
    - 7.2 Custom Hooks
    - 7.3 WebSocket Hooks
8.  Pages
9.  Components
10. Challenge Definition Format
    - 10.1 JSON Schema
    - 10.2 Constraint Types
    - 10.3 Scoring Rules Format
11. Prompt Templates
12. Testing Strategy
    - 12.1 Backend Tests
    - 12.2 Frontend Tests
    - 12.3 Test Fixtures
    - 12.4 E2E Test Flow

---

## 1. Database Schema

All tables use SQLite (via SQLAlchemy 2.0 async + aiosqlite, WAL mode) and SQLModel for model definitions where appropriate. The database is a single local file; it stores all persistent game state. Ephemeral WebSocket state lives in an in-process store (no Redis in the MVP).

### 1.1 SQLModel Models (Python)

File: `backend/app/db/models.py`

```python
from sqlmodel import SQLModel, Field, Column, JSON
from datetime import datetime, date
import uuid

def gen_uuid() -> str:
    return str(uuid.uuid4())

class User(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    guest_id: str | None = Field(default=None, unique=True)
    display_name: str
    email: str | None = None
    password_hash: str | None = None  # set for registered accounts; guests stay None (added Sprint 4)
    detection_rating: float = Field(default=1000.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())

class Challenge(SQLModel, table=True):
    id: str = Field(primary_key=True)  # e.g. "challenge_slogan_01"
    name: str
    interaction_type: str = "Quick Text"
    prompt: str
    constraints: list[dict] = Field(sa_column_kwargs={"type_": "JSON"})
    time_limit_seconds: int = 20
    input_type: str = "text_single_line"
    voting_criteria: str = "most_believable"
    difficulty: int = 2  # 1-5
    scoring_rules: dict = Field(sa_column_kwargs={"type_": "JSON"})
    ai_prompt_template_id: str
    replayability: dict = Field(sa_column_kwargs={"type_": "JSON"})
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())

class ChallengeDaily(SQLModel, table=True):
    date: date = Field(primary_key=True)
    challenge_id: str = Field(foreign_key="challenge.id")
    variant_constraints: list[dict] | None = Field(default=None, sa_column_kwargs={"type_": "JSON"})

class Session(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    challenge_ids: list[str] = Field(sa_column_kwargs={"type_": "JSON"})
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    final_score: int | None = None
    rounds_played: int = 0
    is_daily: bool = False

class Round(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    session_id: str = Field(foreign_key="session.id")
    challenge_id: str = Field(foreign_key="challenge.id")
    round_number: int
    human_entry_id: str | None = None
    ai_entry_id: str | None = None
    vote: str | None = None  # "A" or "B"
    reveal_data: dict = Field(sa_column_kwargs={"type_": "JSON"}, default_factory=dict)
    state: str = "writing"  # writing, reveal_ai, voting, scored
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    time_spent_seconds: float | None = None

class Entry(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    round_id: str = Field(foreign_key="round.id")
    author_type: str  # "human" or "ai"
    content: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    validity: dict = Field(sa_column_kwargs={"type_": "JSON"}, default_factory=dict)
    constraint_violations: list[str] = Field(sa_column_kwargs={"type_": "JSON"}, default_factory=list)

class AIEntry(SQLModel, table=True):
    entry_id: str = Field(foreign_key="entry.id", primary_key=True)
    provider: str  # "openai", "anthropic", "stub"
    model: str
    prompt_version: str
    prompt_hash: str
    raw_response: str
    sanitized_response: str
    token_count: int | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class Vote(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    round_id: str = Field(foreign_key="round.id")
    user_id: str = Field(foreign_key="user.id")
    selected_entry: str  # "A" or "B" (which the player picked as AI)
    voted_at: datetime = Field(default_factory=datetime.utcnow)

class Score(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    round_id: str = Field(foreign_key="round.id")
    base_score: int
    time_bonus: int
    streak_bonus: int
    total_score: int
    scored_at: datetime = Field(default_factory=datetime.utcnow)

class HumanityScore(SQLModel, table=True):
    entry_id: str = Field(foreign_key="entry.id", primary_key=True)
    humanity_score: float  # 0.0 - 100.0
    total_votes: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class Streak(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    type: str = "daily_challenge"  # "daily_challenge", "correct_guess"
    count: int = 0
    last_active_date: date = Field(default_factory=lambda: datetime.utcnow().date())
    longest_record: int = 0

class LeaderboardSnapshot(SQLModel, table=True):
    date: date = Field(primary_key=True)
    user_id: str = Field(foreign_key="user.id", primary_key=True)
    score: int
    rank: int

class PromptAudit(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    prompt_version: str
    prompt_system: str
    prompt_user: str
    challenge_id: str = Field(foreign_key="challenge.id")
    ai_response: str  # sanitized
    raw_response: str  # original
    provider: str
    model: str
    token_count: int | None = None
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
```

**SQLite notes:**

- Models use generic `JSON` columns (not PostgreSQL `JSONB`); SQLite stores them as TEXT with JSON validation handled in Pydantic schemas.
- `connection.py` must enable `PRAGMA foreign_keys=ON` and WAL mode on every connect.
- Primary keys are TEXT UUIDs (as modeled above), so no column type changes are needed for SQLite.

### 1.2 Indexes

```sql
CREATE INDEX idx_users_guest_id ON users(guest_id);
CREATE INDEX idx_users_detection_rating ON users(detection_rating);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_started_at ON sessions(started_at);
CREATE INDEX idx_rounds_session_id ON rounds(session_id);
CREATE INDEX idx_rounds_challenge_id ON rounds(challenge_id);
CREATE INDEX idx_rounds_state ON rounds(state);
CREATE INDEX idx_entries_round_id ON entries(round_id);
CREATE INDEX idx_entries_author_type ON entries(author_type);
CREATE INDEX idx_votes_round_id ON votes(round_id);
CREATE INDEX idx_votes_user_id ON votes(user_id);
CREATE INDEX idx_scores_user_id ON scores(user_id);
CREATE INDEX idx_scores_scored_at ON scores(scored_at);
CREATE INDEX idx_humanity_scores_last_updated ON humanity_scores(last_updated);
CREATE INDEX idx_streaks_user_type ON streaks(user_id, type);
CREATE INDEX idx_leaderboard_date ON leaderboard_snapshots(date);
CREATE INDEX idx_prompt_audit_recorded_at ON prompt_audit(recorded_at);
CREATE INDEX idx_prompt_audit_challenge_id ON prompt_audit(challenge_id);
```

### 1.3 Migrations (Alembic)

Alembic is used for database migrations. Configuration in `alembic.ini` and `backend/alembic/env.py`.

- Initial migration creates all tables from SQLModel metadata.
- Challenge data migrations: populate `challenges` table from `app/data/challenge_library/*.json`.
- Prompt version migrations: tracked in `prompt_audit` table; new versions added via JSON config.
- SQLite: set `render_as_batch=True` in `alembic/env.py` (batch mode) so ALTER operations work.

---

## 2. API Endpoints

All REST endpoints under `http://127.0.0.1:8000/api/v1/`. WebSocket at `ws://127.0.0.1:8000/ws`.

**Auth:** player-scoped endpoints (`/challenges/daily`, all `/session/*`) require a Bearer token (guest or account). Public: `/challenges/{id}`, `/challenges/validate`, and the `/auth/*` endpoints themselves.

### 2.1 Auth

**POST `/auth/guest`**

Create or retrieve a guest session.

- **Request Body:**
  ```json
  {
    "guest_id": "optional-existing-guest-id",
    "display_name": "optional-display-name"
  }
  ```
- **Response (201):**
  ```json
  {
    "user_id": "uuid",
    "guest_id": "uuid-string",
    "display_name": "Player_4829",
    "is_guest": true,
    "token": "jwt-token"
  }
  ```

**POST `/auth/login`**

Login with email + password.

- **Request Body:**
  ```json
  {"email": "user@example.com", "password": "password"}
  ```
- **Response (200):**
  ```json
  {
    "user_id": "uuid",
    "display_name": "Alex",
    "token": "jwt-token"
  }
  ```

**POST `/auth/register`**

Register a new account.

- **Request Body:**
  ```json
  {"email": "user@example.com", "password": "password", "display_name": "Alex"}
  ```
- **Response (201):** Same as login.

**GET `/auth/me`** *(protected — Bearer token)*

Profile for the token holder.

- **Response (200):**
  ```json
  {"user_id": "uuid", "guest_id": "uuid-or-null", "display_name": "Alex", "is_guest": false}
  ```
- **Errors:** 401 without/with an invalid token.

### 2.2 Challenges

**GET `/challenges/daily`**

Get today's daily challenge. If the player has no active session, this starts a new daily session.

- **Query:** `?player_rating=1050` (optional, for adaptive difficulty)
- **Response (200):**
  ```json
  {
    "challenge": {
      "id": "challenge_slogan_01",
      "name": "Tiny Tagline",
      "prompt": "Write a slogan for a dragon-owned bakery.",
      "constraints": [{"type": "max_words", "value": 5, "isHard": true}],
      "time_limit_seconds": 15,
      "input_type": "text_single_line",
      "voting_criteria": "most_believable",
      "difficulty": 2
    },
    "session_id": "session-uuid",
    "round_number": 1
  }
  ```

**GET `/challenges/{challenge_id}`**

Get a single challenge definition.

- **Response (200):** Full `ChallengeDefinition` JSON.

**POST `/challenges/validate`**

Validate an entry against a challenge's constraints (soft check only — hard validation happens server-side in the voting flow).

- **Request Body:**
  ```json
  {"challenge_id": "challenge_slogan_01", "entry": "Fire-baked bread, dragon-approved"}
  ```
- **Response (200):**
  ```json
  {
    "valid": true,
    "hard_violations": [],
    "soft_violations": [],
    "word_count": 5,
    "character_count": 33
  }
  ```

### 2.3 Session

**POST `/session/start`**

Start a new session (daily or practice).

- **Request Body:**
  ```json
  {
    "type": "daily",
    "challenge_ids": ["challenge_slogan_01", "challenge_caption_02", ...]
  }
  ```
- **Response (201):**
  ```json
  {
    "session_id": "uuid",
    "type": "daily",
    "rounds_total": 3,
    "next_challenge": {"id": "challenge_slogan_01", "prompt": "...", "time_limit_seconds": 15}
  }
  ```

**GET `/session/{session_id}`**

Get session status.

- **Response (200):**
  ```json
  {
    "session_id": "uuid",
    "type": "daily",
    "current_round": 1,
    "rounds_total": 3,
    "state": "in_progress",
    "started_at": "2026-08-03T10:30:00Z",
    "completed_at": null
  }
  ```

**GET `/session/{session_id}/summary`**

Get session summary after completion.

- **Response (200):**
  ```json
  {
    "session_id": "uuid",
    "type": "daily",
    "total_score": 275,
    "accuracy": 66.7,
    "rounds": [
      {
        "round_number": 1,
        "challenge_id": "challenge_slogan_01",
        "vote": "B",
        "correct": true,
        "score": 125,
        "humanity_human": 72,
        "humanity_ai": 55
      }
    ],
    "rating_change": "+12",
    "streak": 3
  }
  ```

### 2.4 Leaderboard

**GET `/leaderboard/daily`**

Today's leaderboard.

- **Query:** `?date=2026-08-03&limit=100`
- **Response (200):**
  ```json
  {
    "date": "2026-08-03",
    "entries": [
      {"rank": 1, "display_name": "Alex", "score": 300, "accuracy": 100.0},
      {"rank": 2, "display_name": "Jordan", "score": 275, "accuracy": 66.7}
    ]
  }
  ```

**GET `/leaderboard/all-time`**

All-time leaderboard by Detection Rating.

- **Query:** `?limit=100`
- **Response (200):**
  ```json
  {
    "entries": [
      {"rank": 1, "display_name": "Morgan", "rating": 1450},
      {"rank": 2, "display_name": "Sam", "rating": 1380}
    ]
  }
  ```

### 2.5 Profile

**GET `/profile`**

Get current user's profile + stats.

- **Response (200):**
  ```json
  {
    "user_id": "uuid",
    "display_name": "Player_4829",
    "is_guest": true,
    "detection_rating": 1012,
    "total_rounds": 47,
    "overall_accuracy": 62.3,
    "current_streak": 3,
    "longest_streak": 7,
    "daily_challenge_streak": 5,
    "recent_humanity_scores": [
      {"challenge_id": "challenge_slogan_01", "score": 68, "date": "2026-08-03"}
    ]
  }
  ```

**PUT `/profile`**

Update profile (display name).

- **Request Body:**
  ```json
  {"display_name": "NewName"}
  ```
- **Response (200):** Updated profile.

### 2.6 Share

**POST `/share/result`**

Generate a shareable result card for a completed session.

- **Request Body:**
  ```json
  {
    "session_id": "uuid",
    "format": "image",  // or "text"
    "message": "Got 2/3 on today's challenge!"
  }
  ```
- **Response (200):**
  ```json
  {
    "share_text": "I scored 275 on today's Man vs. Machine daily challenge! Can you beat my accuracy? #ManVsMachine",
    "share_url": "/s/abc123"  # local route to view the result
  }
  ```

### 2.7 Voting

**POST `/voting/submit-entry`** (Sprint 10; the vote endpoint arrives with VotingService in Sprint 11)

Validate a human entry and trigger AI generation. Hard violations block the
submission; soft violations are reported but allowed. The prompt + both
responses are recorded in `prompt_audit` (§8).

- **Auth:** Bearer token
- **Request Body:**
  ```json
  {"challenge_id": "challenge_slogan_01", "entry": "Fire baked. Dragon approved."}
  ```
- **Response (200):**
  ```json
  {
    "challenge_id": "challenge_slogan_01",
    "human_entry": "Fire baked. Dragon approved.",
    "ai_entry": "Dragon's fire, fresh baked.",
    "provider": "ollama",
    "model": "qwen3.5:9b",
    "hard_violations": [],
    "soft_violations": []
  }
  ```
- **Errors:** 401 (no/invalid token), 404 (unknown challenge), 400 (hard
  violations or invalid input; `detail.hard_violations` lists them), 503 (every
  provider in the chain failed — should not happen: StubProvider is always last).

---

## 3. WebSocket API


All WebSocket events are JSON-serialized.

### 3.1 Connection

- **Endpoint:** `ws://127.0.0.1:8000/ws/session/{session_id}`
- **Auth:** JWT token in query parameter `?token=...`
- **Subprotocol:** `manvs.protocol.v1`

### 3.2 Events

#### Client → Server

| Event | Payload | Description |
|-------|---------|-------------|
| `SUBMIT_ENTRY` | `{sessionId, roundId, entry: "text..."}` | Player submits their answer |
| `VOTE` | `{sessionId, roundId, vote: "A"\|"B"}` | Player casts their vote |
| `PING` | `{}` | Keepalive |

#### Server → Client

| Event | Payload | Description |
|-------|---------|-------------|
| `SESSION_STARTED` | `{sessionId, rounds: number, challenges: ChallengeBrief[]}` | Session begins |
| `ROUND_START` | `{roundId, roundNumber, challenge, timeLimitSeconds}` | Next round begins |
| `AI_RESPONSE_READY` | `{roundId, entries: {A: string, B: string}}` | Both entries ready; voting begins |
| `VOTE_CONFIRMED` | `{roundId, vote: "A"\|"B"}` | Server acknowledges vote |
| `REVEAL` | `{roundId, humanWas: "A"\|"B", humanityHuman: 0-100, humanityAI: 0-100, explanation: "string"}` | Reveal results |
| `ROUND_SCORED` | `{roundId, score: {base, timeBonus, streakBonus, total}, ratingChange, streakUpdate}` | Scoring complete |
| `SESSION_END` | `{sessionId, summary: SessionSummary}` | All rounds complete |
| `ERROR` | `{code: string, message: string}` | Error state |
| `PONG` | `{}` | Pong response to PING |

**Timing constraints:**
- `SUBMIT_ENTRY` must arrive during the WRITING phase. Late submissions are accepted but penalized.
- `VOTE` must arrive during the VOTING phase. If the 15-second vote window expires, the vote defaults to random.
- The server does not proceed to REVEAL until both entries are ready AND a vote is received (or the vote window expires).

---

## 4. Repositories

### 4.1 UserRepository

File: `backend/app/repositories/user.py`

| Method | Signature | Description |
|--------|-----------|-------------|
| `create_guest` | `(display_name: str) -> User` | Create a guest user with auto-generated name |
| `get_by_id` | `(user_id: str) -> User` | Fetch by ID |
| `get_by_guest_id` | `(guest_id: str) -> User \| None` | Fetch guest user |
| `update_rating` | `(user_id: str, new_rating: float) -> User` | Update detection rating |
| `update_display_name` | `(user_id: str, name: str) -> User` | Update display name |
| `get_leaderboard` | `(limit: int = 100) -> list[LeaderboardEntry]` | Top rated users |

### 4.2 ChallengeRepository

File: `backend/app/repositories/challenge.py`

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_id` | `(challenge_id: str) -> Challenge` | Fetch single challenge |
| `get_daily` | `(date: date) -> Challenge` | Today's daily challenge |
| `create` | `(challenge: ChallengeCreate) -> Challenge` | Insert new challenge |
| `get_all_ids` | `() -> list[str]` | All challenge IDs (for rotation) |
| `increment_daily_usage` | `(challenge_id: str) -> None` | Track challenge usage |

### 4.3 SessionRepository

File: `backend/app/repositories/session.py`

| Method | Signature | Description |
|--------|-----------|-------------|
| `create` | `(user_id: str, challenge_ids: list[str], is_daily: bool) -> Session` | Start new session |
| `get` | `(session_id: str) -> Session` | Fetch session |
| `update_state` | `(session_id: str, state: str) -> Session` | Update session state |
| `complete` | `(session_id: str, final_score: int) -> Session` | Mark session complete |
| `get_user_sessions` | `(user_id: str, limit: int = 20) -> list[Session]` | Recent sessions |
| `get_active_daily_session` | `(user_id: str, for_date: date) -> Session \| None` | Uncompleted daily session started on a date (Sprint 7) |

### 4.4 VotingRepository

File: `backend/app/repositories/voting.py`

| Method | Signature | Description |
|--------|-----------|-------------|
| `create_vote` | `(round_id: str, user_id: str, vote: str) -> Vote` | Record a vote |
| `get_votes_for_round` | `(round_id: str) -> list[Vote]` | All votes in a round |
| `record_reveal` | `(round_id: str, human_was: str, reveal_data: dict) -> Round` | Mark round revealed |
| `get_entries_anonymized` | `(round_id: str) -> dict[str, str]` | Returns {"A": "...", "B": "..."} |

### 4.5 ScoringRepository

File: `backend/app/repositories/scoring.py`

| Method | Signature | Description |
|--------|-----------|-------------|
| `create_score` | `(user_id, round_id, base, time_bonus, streak_bonus, total) -> Score` | Record a score |
| `get_daily_scores` | `(date: date, limit: int = 100) -> list[LeaderboardEntry]` | Daily leaderboard |
| `get_user_rating` | `(user_id: str) -> float` | Current detection rating |
| `update_streak` | `(user_id: str, streak_type: str, count: int) -> Streak` | Update streak counter |

### 4.6 PromptAuditRepository

File: `backend/app/repositories/prompt_audit.py`

| Method | Signature | Description |
|--------|-----------|-------------|
| `record` | `(prompt_version, system_prompt, user_prompt, challenge_id, response, raw_response, provider, model, token_count) -> PromptAudit` | Log a prompt+response |
| `get_by_challenge` | `(challenge_id: str) -> list[PromptAudit]` | All prompts used for a challenge |
| `get_versions` | `() -> list[str]` | All distinct prompt versions |

---

## 5. Services

### 5.1 ChallengeService

File: `backend/app/services/challenge_service.py`

```python
class ChallengeService:
    def __init__(self, challenge_repo: ChallengeRepository):
        self.repo = challenge_repo

    def get_challenge(self, challenge_id: str) -> ChallengeDefinition
    def get_daily_challenge(self, date: date, player_rating: float | None = None) -> ChallengeDefinition
    def apply_constraints(self, entry: str, challenge: ChallengeDefinition) -> ConstraintResult
    def validate_input(self, entry: str, input_type: str) -> ValidationResult
    def generate_time_limit(self, challenge: ChallengeDefinition, difficulty: int) -> int
    def rotate_daily_challenge(self, date: date) -> ChallengeDefinition
    def get_challenge_pool(self) -> list[str]  # All challenge IDs
```

### 5.2 AIService

File: `backend/app/services/ai_service.py`

```python
class AIService:
    def __init__(self, config: Settings, content_filter: ContentFilter,
                 audit_service: PromptAuditService,
                 providers: list[AIProvider] | None = None):
        self.providers: list[AIProvider] = []  # from build_provider_chain(config)
        self.active_provider: AIProvider | None = None

    async def generate_entry(self, challenge: ChallengeDefinition, retry_on_injection: int = 3) -> str
    def build_prompt(self, challenge: ChallengeDefinition) -> str  # user prompt from the template
    def build_system_prompt(self, challenge: ChallengeDefinition) -> str  # template + humanity guidance
    def get_humanity_guidance(self, challenge: ChallengeDefinition) -> str
    def select_provider(self) -> AIProvider  # first available; delegates to §6.6 logic
    async def aclose(self) -> None  # release provider HTTP clients
```

`generate_entry` walks the provider chain: a provider that fails (any
`ProviderError`) or returns a rejected response (empty, meta-mention, injection)
is skipped after up to `retry_on_injection` attempts, and the chain continues.
The accepted response is sanitized (`ContentFilter.sanitize_ai_response`), then
recorded via `PromptAuditService.record_usage` (raw + sanitized, provider, model)
before being returned. Only if every provider fails does it raise
`ProviderUnavailable`.

### 5.3 VotingService

File: `backend/app/services/voting_service.py`

```python
class VotingService:
    def __init__(self, repo: VotingRepository):
        self.repo = repo

    def present_entries(self, human_entry: str, ai_entry: str) -> dict[str, str]
        """Returns {"A": "entry text", "B": "entry text"} with randomized assignment."""

    def process_vote(self, round_id: str, vote: str) -> VoteResult
        """Records vote, determines if round can proceed to reveal."""

    def reveal(self, round_id: str) -> RevealResult
        """Determines which entry was human/AI, generates explanation."""
```

### 5.4 ScoringService

File: `backend/app/services/scoring_service.py`

```python
class ScoringService:
    def __init__(self, repo: ScoringRepository, user_repo: UserRepository):
        self.repo = repo
        self.user_repo = user_repo

    def calculate_round_score(self, vote_correct: bool, time_remaining: float,
                              time_limit: float, streak: int, challenge: ChallengeDefinition) -> RoundScore
    def calculate_rating_change(self, player_rating: float, ai_humanity_score: float,
                                vote_correct: bool) -> float
    def update_humanity_score(self, entry_id: str, votes: list[Vote], is_ai: bool) -> float
    def get_current_streak(self, user_id: str, streak_type: str) -> int
    def update_streak(self, user_id: str, streak_type: str, correct: bool) -> int
    def get_daily_leaderboard(self, date: date, limit: int = 100) -> list[dict]
```

### 5.5 SessionService

File: `backend/app/services/session_service.py`

```python
class SessionService:
    def __init__(self, session_repo, challenge_service, ai_service, voting_service, scoring_service):
        ...

    def start_session(self, user_id: str, session_type: str, challenge_ids: list[str] | None = None) -> Session
    def get_round_state(self, round_id: str) -> str  # "writing", "reveal_ai", "voting", "scored"
    def transition_round(self, round_id: str, target_state: str) -> bool
    def complete_round(self, round_id: str) -> RoundSummary
    def start_next_round(self, session_id: str) -> RoundState
    def get_session_summary(self, session_id: str) -> SessionSummary
```

### 5.6 ContentFilter

File: `backend/app/services/content_filter.py`

```python
class ContentFilter:
    META_PATTERNS: list[str] = [
        "as an AI", "as a language model", "I'm an AI", "I'm a language model",
        "as an artificial intelligence", "I don't have feelings", "I'm not capable of"
    ]
    INJECTION_PATTERNS: list[str] = [
        "ignore all previous instructions", "new instructions:", "system prompt",
        "you are now", "you are a different"
    ]
    LEAKAGE_PATTERNS: list[str]  # injection patterns + first-person instruction references;
        # sentences matching any are dropped by strip_system_prompt_leakage
    MAX_RESPONSE_LENGTH = 500

    def sanitize(self, raw: str, max_length: int = 500) -> str
    def sanitize_ai_response(self, raw: str, max_length: int = 500) -> str  # Sprint 8 name; sanitize aliases it
    def check_prompt_injection(self, text: str) -> InjectionRisk
    def check_meta_mentions(self, text: str) -> list[str]  # returns found patterns
    def validate_no_meta_mentions(self, text: str) -> bool
    def strip_system_prompt_leakage(self, text: str) -> str
    def validate_response(self, raw: str, challenge: ChallengeDefinition) -> ValidationResult
```

### 5.7 PromptAuditService

File: `backend/app/services/prompt_audit_service.py`

```python
class PromptAuditService:
    def get_prompt_template(self, version: str) -> PromptTemplate
    def get_active_version(self) -> str
    def record_usage(self, challenge_id: str, prompt: str, response: str,
                     provider: str, model: str, token_count: int | None = None,
                     raw_response: str | None = None, prompt_version: str | None = None) -> PromptAudit
    def list_versions(self) -> list[str]  # template versions available in app/data/ai_prompts/

class PromptTemplate:
    version: str
    system_prompt: str
    user_template: str  # may contain {prompt}, {constraints}, {time_limit}
    instructions: list[str]
    humanity_guidance: list[str]
```

### 5.8 ShareService

File: `backend/app/services/share_service.py`

```python
class ShareService:
    def generate_share_text(self, session_summary: SessionSummary) -> str
    def generate_share_image(self, session_summary: SessionSummary) -> bytes  # PNG
    def create_share_link(self, session_id: str) -> str  # for viewing a replay
```

---

## 6. AI Provider Integration

### 6.1 Provider Interface

File: `backend/app/services/ai/providers/base.py`

```python
class AIProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str, 
                       temperature: float = 0.7, max_tokens: int = 100,
                       *, challenge_id: str | None = None) -> str
    @abstractmethod
    def is_available(self) -> bool
    @abstractmethod
    def get_model_name(self) -> str
    @abstractmethod
    def get_provider_name(self) -> str

class ProviderError(Exception):
    pass

class ProviderUnavailable(ProviderError):
    pass
```

`generate` takes an optional keyword-only `challenge_id`: external providers ignore
it, while StubProvider needs it to pick the right entry pool.

### 6.2 OpenAIProvider

File: `backend/app/services/ai/providers/openai_provider.py`

```python
class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout: int = 30):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def generate(self, prompt: str, system_prompt: str,
                       temperature: float = 0.7, max_tokens: int = 100) -> str:
        # Calls https://api.openai.com/v1/chat/completions
        # Returns only the content field from the response
        ...
```

### 6.3 AnthropicProvider

File: `backend/app/services/ai/providers/anthropic_provider.py`

- Uses `https://api.anthropic.com/v1/messages`
- Same interface, different endpoint and request format
- Model: `claude-3-haiku-20240307` (primary for cost/speed)

### 6.4 OllamaProvider

File: `backend/app/services/ai/providers/ollama_provider.py`

- Local LLM option (Scope Constraint 7): no API key, no external call.
- Calls `POST {base_url}/api/generate` with `stream: false` and `think: false`
  (qwen3-family models otherwise spend the token budget on hidden reasoning and
  return an empty visible response — found in the Sprint 9 bake-off).
- `is_available()` probes `GET {base_url}/api/version` (localhost round-trip).
- Defaults: `http://127.0.0.1:11434`, model `qwen3.5:9b` (bake-off winner on a
  4GB-VRAM machine); both configurable via `OLLAMA_BASE_URL` / `OLLAMA_MODEL`,
  and the provider can be removed from the chain with `OLLAMA_ENABLED=false`.

```python
class OllamaProvider(AIProvider):
    def __init__(self, base_url: str = "http://127.0.0.1:11434",
                 model: str = "qwen3.5:9b", timeout: int = 120):
        ...
```

### 6.5 StubProvider

File: `backend/app/services/ai/providers/stub_provider.py`

- **Critical for testing.** No API keys required.
- Returns entries from a pre-written pool keyed by challenge_id.
- Pool lives in `app/data/stub_entries/{challenge_id}.json`.
- Each pool has 10-20 human-written-quality entries.

```python
class StubProvider(AIProvider):
    def __init__(self, stub_dir: str):
        self.stub_dir = stub_dir  # app/data/stub_entries/

    async def generate(self, prompt: str, system_prompt: str, ...) -> str:
        # Hash the prompt to select deterministically from the pool
        # Ensures reproducibility across runs
        ...
```

### 6.6 Provider Selection Logic

```python
# providers/__init__.py (Sprint 9)
def build_provider_chain(config: Settings | None = None) -> list[AIProvider]:
    """Ordered chain: OpenAI (key) -> Anthropic (key) -> Ollama (enabled) -> Stub.
    STUB_PROVIDER_ONLY=true collapses it to [StubProvider] (E2E tests)."""

def select_provider(providers: list[AIProvider]) -> AIProvider:
    """First provider whose is_available() is True (Stub is always last)."""
```

Chain order and selection are implemented in `providers/__init__.py`; Sprint 10's
`AIService.select_provider()` delegates to these. Errors map as: non-2xx ->
`ProviderError`; connection refused / timeout -> `ProviderUnavailable`. AIService
catches both and moves down the chain.

---

## 7. Frontend State Management

### 7.1 React Contexts

#### SessionContext
File: `frontend/src/contexts/SessionContext.tsx`

```typescript
interface SessionContextType {
  session: Session | null;
  currentRound: Round | null;
  challenge: ChallengeDefinition | null;
  gameState: 'idle' | 'writing' | 'reveal_ai' | 'voting' | 'score' | 'complete';
  timeRemaining: number;
  startSession: (type: 'daily' | 'practice') => Promise<void>;
  submitEntry: (entry: string) => Promise<void>;
  submitVote: (vote: 'A' | 'B') => Promise<void>;
  nextRound: () => Promise<void>;
}
```

#### VotingContext
File: `frontend/src/contexts/VotingContext.tsx`

```typescript
interface VotingContextType {
  entries: { A: string; B: string } | null;
  humanWas: 'A' | 'B' | null;
  humanityScores: { human: number; ai: number } | null;
  explanation: string | null;
  vote: 'A' | 'B' | null;
  isVoting: boolean;
}
```

#### ScoringContext
File: `frontend/src/contexts/ScoringContext.tsx`

```typescript
interface ScoringContextType {
  roundScore: RoundScore | null;
  sessionSummary: SessionSummary | null;
  ratingChange: number | null;
  streak: number;
  isLoading: boolean;
}
```

#### AuthContext
File: `frontend/src/contexts/AuthContext.tsx`

```typescript
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isGuest: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  loginAsGuest: () => Promise<void>;
  logout: () => void;
}
```

### 7.2 Custom Hooks

| Hook | File | Description |
|------|------|-------------|
| `useSession` | `hooks/useSession.ts` | Session lifecycle, round transitions |
| `useVoting` | `hooks/useVoting.ts` | Entries, vote submission, reveal |
| `useTimer` | `hooks/useTimer.ts` | Countdown timer with urgency states |
| `useLeaderboard` | `hooks/useLeaderboard.ts` | Fetch leaderboard data |
| `useAuth` | `hooks/useAuth.ts` | Auth state, login/register/guest |
| `useChallenges` | `hooks/useChallenges.ts` | Fetch challenge definitions |
| `useScoring` | `hooks/useScoring.ts` | Score display, rating changes |
| `useShare` | `hooks/useShare.ts` | Share result generation |

### 7.3 WebSocket Hooks

| Hook | File | Description |
|------|------|-------------|
| `useWebSocket` | `websocket/hooks.ts` | Core WebSocket connection, event dispatch |
| `useRoundState` | `websocket/hooks.ts` | Subscribes to ROUND_START, AI_RESPONSE_READY, REVEAL, ROUND_SCORED |
| `useSessionEvents` | `websocket/hooks.ts` | Subscribes to SESSION_STARTED, SESSION_END |

```typescript
// Core WebSocket event types
type WSEvent = 
  | { type: 'SESSION_STARTED'; session_id: string; rounds: number; challenges: ChallengeBrief[] }
  | { type: 'ROUND_START'; round_id: string; round_number: number; challenge: ChallengeDefinition; time_limit_seconds: number }
  | { type: 'AI_RESPONSE_READY'; round_id: string; entries: { A: string; B: string } }
  | { type: 'REVEAL'; round_id: string; human_was: 'A' | 'B'; humanity_human: number; humanity_ai: number; explanation: string }
  | { type: 'ROUND_SCORED'; round_id: string; score: RoundScore; rating_change: number; streak_update: StreakUpdate }
  | { type: 'SESSION_END'; session_id: string; summary: SessionSummary }
  | { type: 'ERROR'; code: string; message: string };
```

---

## 8. Pages

| Page | File | Purpose |
|------|------|---------|
| `Home` | `pages/Home.tsx` | Daily challenge prompt, streak indicator, leaderboard preview, practice button |
| `Session` | `pages/Session.tsx` | Full 3-round session flow: challenge → write → vote → reveal → score → next |
| `Challenge` | `pages/Challenge.tsx` | Single challenge view (for practice mode, standalone) |
| `Leaderboard` | `pages/Leaderboard.tsx` | Daily and all-time leaderboards |
| `Profile` | `pages/Profile.tsx` | User stats, detection rating, streak history, humanity score trends |
| `Auth` | `pages/Auth.tsx` | Guest login, email/password login/register |
| `Settings` | `pages/Settings.tsx` | Theme, AI provider selection (stub/local), sound toggle |

### Route Map

```
/                 → Home
/session          → Session (active session)
/session/:id      → Session (view past session)
/leaderboard      → Leaderboard
/profile          → Profile
/auth             → Auth
/settings         → Settings
```

---

## 9. Components

### 9.1 Reusable Components

| Component | Description |
|-----------|-------------|
| `Timer` | Countdown display with urgency color shift (green → yellow → red) |
| `EntryInput` | Text input for human entry, with live word/character count |
| `VotingScreen` | A/B entry display, vote buttons, randomization indicator |
| `RevealScreen` | Flip animation revealing which was AI, humanity scores, explanation |
| `ScoreAnimation` | Animated score counter with breakdown |
| `RatingDisplay` | Detection rating with change indicator (+/-) |
| `StreakBadge` | Daily streak counter with fire icon |
| `ChallengeView` | Prompt display, constraints rendering, time limit |
| `SessionSummary` | End-of-session stats, share button |
| `ResultCard` | Shareable image/text summary |
| `LeaderboardTable` | Sortable table with rank, name, score/rating |
| `HumanityMeter` | 0-100 bar showing how human-like an entry appears |

### 9.2 Component Props (Key Examples)

```typescript
interface VotingScreenProps {
  entries: { A: string; B: string };
  onVote: (choice: 'A' | 'B') => void;
  timeRemaining?: number;  // optional vote window timer
  entryType: 'bluff';
}

interface RevealScreenProps {
  humanWas: 'A' | 'B';
  humanEntry: string;
  aiEntry: string;
  humanityHuman: number;
  humanityAI: number;
  explanation: string;
  onNext: () => void;
}

interface TimerProps {
  seconds: number;
  totalSeconds: number;
  urgencyThreshold?: number;  // when to switch to red (default: 5s)
}

interface EntryInputProps {
  maxLength?: number;      // auto from challenge constraints
  maxWords?: number;
  placeholder?: string;
  onSubmit: (entry: string) => void;
  onValidationError?: (errors: string[]) => void;
}
```

---

## 10. Challenge Definition Format

### 10.1 JSON Schema

Challenge definitions live as individual JSON files in `backend/app/data/challenge_library/`. Each file is named `{challenge_id}.json`.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "interactionType", "prompt", "constraints",
               "timeLimitSeconds", "inputType", "votingCriteria", "difficulty",
               "scoringRules", "aiPromptTemplateId", "aiPromptGuidance", "replayability"],
  "properties": {
    "id": { "type": "string", "pattern": "^challenge_[a-z0-9]+_[0-9]+$" },
    "name": { "type": "string" },
    "interactionType": { "type": "string", "enum": ["Quick Text"] },
    "prompt": { "type": "string" },
    "constraints": {
      "type": "array",
      "items": { "$ref": "#/definitions/constraint" }
    },
    "timeLimitSeconds": { "type": "integer", "minimum": 10, "maximum": 120 },
    "inputType": { "type": "string", "enum": ["text_single_line", "text_multi_line"] },
    "votingCriteria": { "type": "string", "enum": ["most_believable"] },
    "difficulty": { "type": "integer", "minimum": 1, "maximum": 5 },
    "scoringRules": { "$ref": "#/definitions/scoringRules" },
    "aiPromptTemplateId": { "type": "string" },
    "aiPromptGuidance": { "type": "string" },
    "replayability": { "$ref": "#/definitions/replayability" }
  },
  "definitions": {
    "constraint": {
      "type": "object",
      "required": ["type", "isHard"],
      "properties": {
        "type": { "type": "string", "enum": ["max_words", "max_characters", 
                   "must_rhyme", "no_adjectives", "must_include_theme", 
                   "exactly_n_emojis", "no_letter_e", "one_sentence_only"] },
        "value": { "type": ["number", "string", "array"] },
        "isHard": { "type": "boolean" },
        "description": { "type": "string" }
      }
    },
    "scoringRules": {
      "type": "object",
      "required": ["baseScore", "timeBonusMultiplier", "streakMultiplier"],
      "properties": {
        "baseScore": { "type": "integer", "default": 100 },
        "timeBonusMultiplier": { "type": "number", "default": 0.1 },
        "streakMultiplier": { "type": "number", "default": 0.05 }
      }
    },
    "replayability": {
      "type": "object",
      "properties": {
        "dailyVariants": { "type": "integer", "default": 1 },
        "constraintPool": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

### 10.2 Constraint Types

| Type | Value | Behavior | Hard/Soft |
|------|-------|----------|-----------|
| `max_words` | integer | Rejects submissions exceeding N words | Hard |
| `max_characters` | integer | Rejects submissions exceeding N characters | Hard |
| `must_rhyme` | (none) | Entry should rhyme — checked post-hoc | Soft |
| `no_adjectives` | (none) | Entry should avoid adjectives — checked post-hoc | Soft |
| `must_include_theme` | string/array | Entry must contain a keyword from the theme | Hard |
| `exactly_n_emojis` | integer | Entry must contain exactly N emojis | Hard |
| `no_letter_e` | (none) | Entry must not use the letter "e" | Hard |
| `one_sentence_only` | (none) | Entry must be a single sentence | Hard |

### 10.3 Scoring Rules Format

```json
{
  "baseScore": 100,
  "timeBonusMultiplier": 0.1,  // 10% of base per second remaining (capped at 50%)
  "streakMultiplier": 0.05    // 5% of base per consecutive correct guess
}
```

**Total score** = `baseScore * (vote_correct: 1.0 : 0.0) + timeBonus + streakBonus`
- `timeBonus = min(baseScore * 0.5, baseScore * timeBonusMultiplier * time_remaining / time_limit)`
- `streakBonus = baseScore * streakMultiplier * current_streak` (only if vote was correct)

---

## 11. Prompt Templates

File: `backend/app/data/ai_prompts/v1.0.json`

```json
{
  "version": "v1.0",
  "system_prompt": "You are a creative assistant. Your task is to complete a creative micro-challenge. Write your response as if you are a human with {time_limit} seconds to think. Be naturally imperfect: you may use slightly casual phrasing, minor grammatical quirks, or offhand observations. Do NOT acknowledge you are an AI. Do NOT mention this is a prompt. Do NOT add explanations or commentary. Just output your entry.",
  "user_template": "Challenge: {prompt}\n\nConstraints:\n{constraints_formatted}\n\nYour entry:",
  "instructions": [
    "Do not acknowledge you are an AI",
    "Do not mention being a language model", 
    "Do not reference system prompts or instructions",
    "Write naturally as a human under time pressure",
    "Introduce minor imperfections (casual tone, slight grammar quirks)",
    "Do not add commentary or explanations",
    "Output only the entry text"
  ],
  "humanity_guidance": [
    "Add a casual aside or qualifier",
    "Use colloquial contractions (don't, can't, won't)",
    "Occasionally trail off or hesitate in phrasing",
    "Reference something slightly mundane or personal"
  ]
}
```

The `humanity_guidance` list is appended to the system prompt as additional instructions to encourage "detectable imperfections" — the opposite of what you'd want from a polished AI response.

---

## 12. Testing Strategy

### 12.1 Backend Tests (pytest + pytest-asyncio)

| Test Module | Focus |
|-------------|-------|
| `test_challenge_engine.py` | Constraint validation (hard/soft), time limit calc, daily rotation determinism |
| `test_ai_service.py` | Prompt construction, provider selection, fallback to StubProvider, sanitization, audit recording |
| `test_ai_providers.py` | Provider ABC contract, per-provider payloads/error mapping (MockTransport), chain build + selection fall-through |
| `test_api_voting.py` | `POST /voting/submit-entry`: both entries returned, soft/hard violation handling, auth, 404/400/503 mapping, audit row |
| `test_content_filter.py` | Meta-mention detection, injection pattern matching, response length limits |
| `test_voting.py` | A/B randomization (seeded), vote processing, reveal correctness |
| `test_scoring.py` | Score formula, ELO rating math, humanity score calc, streak logic |
| `test_session.py` | State machine transitions, round lifecycle, session summary |
| `test_websocket.py` | Event dispatching, connection auth, error handling |
| `test_prompt_audit.py` | Prompt versioning, audit recording, reproducibility |
| `test_e2e.py` | Full flow with StubProvider: challenge → entry → AI → vote → reveal → score |

### 12.2 Frontend Tests (Vitest)

| Test Module | Focus |
|-------------|-------|
| `Timer.test.tsx` | Countdown, urgency states, auto-submit at 0 |
| `EntryInput.test.tsx` | Text input, word/char counting, validation feedback |
| `VotingScreen.test.tsx` | A/B display, vote button behavior, no peeking |
| `RevealScreen.test.tsx` | Correct reveal, humanity display, explanation text |
| `ScoreAnimation.test.tsx` | Score display, animation timing |

### 12.3 Test Fixtures

| File | Purpose |
|------|---------|
| `backend/tests/fixtures/challenges/` | 5 sample challenge definitions in JSON |
| `backend/tests/fixtures/stub_entries/` | Pre-written entries for StubProvider per challenge |
| `backend/tests/fixtures/ai_prompts/` | Prompt template v1.0 |
| `frontend/tests/fixtures/` | Mock WebSocket events, sample entries, session summaries |

### 12.4 E2E Test Flow

1.  Start backend with `STUB_PROVIDER_ONLY=true` (no real API keys needed)
2.  POST `/session/start` → get session_id with 3 challenges
3.  Connect WebSocket to `/ws/session/{session_id}`
4.  Receive `ROUND_START` → verify challenge prompt + time limit displayed
5.  Send `SUBMIT_ENTRY` with a valid entry → verify accepted
6.  Receive `AI_RESPONSE_READY` → verify both entries shown anonymized (A/B)
7.  Verify player's own entry is hidden (no indication of which is theirs)
8.  Send `VOTE` → verify `VOTE_CONFIRMED`
9.  Receive `REVEAL` → verify correct attribution + humanity scores
10. Receive `ROUND_SCORED` → verify score calculation
11. After round 3, receive `SESSION_END` → verify session summary
12. GET `/leaderboard/daily` → verify player appears
13. POST `/share/result` → verify share text generated

---

*This is Document 2 of 5. For architecture overview, see `docs/01_Master_Architecture.md`. For the sprint roadmap, see `docs/03_Sprint_Plan.md`. For challenge definitions, see `docs/05_Micro_Challenge_Library.md`.*
