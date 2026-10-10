# Man vs. Machine — Sprint Plan

> **Version:** 1.0
> **Status:** Draft — Sprint 0 (Pre-MVP)
> **Audience:** Developers, AI coding agents
> **Related:** See `docs/01_Master_Architecture.md` for architecture overview and `docs/02_Implementation_Guide.md` for technical reference.

This document is the **day-to-day build guide** for Man vs. Machine. It breaks the MVP into 20 incremental sprints across 7 phases. Each sprint is self-contained and designed to be completed and verified before moving to the next.

---

## Sprint Planning Methodology

Each sprint follows this template:

| Field | Description |
|-------|-------------|
| **Objective** | What this sprint accomplishes in one sentence |
| **Inputs** | Data, files, or context needed to start |
| **Outputs** | Deliverables produced by this sprint |
| **Files Created** | New files to create |
| **Files Modified** | Existing files to change |
| **Database Changes** | Any schema changes |
| **Backend Changes** | Service, repository, or API updates |
| **Frontend Changes** | UI component, page, or hook updates |
| **API Endpoints** | New or modified endpoints |
| **Acceptance Criteria** | Specific, testable conditions |
| **Manual Testing** | Step-by-step verification checklist |
| **Definition of Done** | What "done" means for this sprint |
| **Estimated Time** | Rough developer time (AI agent) |
| **Dependencies** | Which previous sprints must be done first |

---

## Sprint Phases Overview

| Phase | Sprints | Description |
|-------|---------|-------------|
| Phase 0 | 1-4 | Foundation: project scaffolding, local dev config (no Docker), AGENTS.md |
| Phase 1 | 5-7 | Database & schema, repositories, API scaffolding, auth |
| Phase 2 | 8-10 | Challenge Engine: data files, constraint engine, challenge API |
| Phase 3 | 11-14 | AI Layer: content filter, prompt audit, provider abstraction, AIService |
| Phase 4 | 15-18 | Voting & Scoring: VotingService, ScoringService, SessionService, WebSocket |
| Phase 5 | 19-22 | Frontend foundation: scaffolding, API client, contexts, auth |
| Phase 6 | 23-26 | Game UI: ChallengeView, VotingScreen, RevealScreen, Session flow |
| Phase 7 | 27-29 | Leaderboard, Profile, Result cards, share, E2E tests |

---

## Phase 0: Foundation (Sprints 1-4)

### Sprint 1 — Project Scaffolding & AGENTS.md

**Objective:** Set up the project root with a local dev setup (no Docker), configuration, AGENTS.md, and the basic FastAPI/Vite project skeletons.

**Files Created:**
- `AGENTS.md` (project operating contract)
- `scripts/dev.py` (one-command local dev: backend + frontend + SQLite init)
- `backend/pyproject.toml`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/requirements.txt`
- `.python-version`
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/app.tsx`

**Files Modified:**
- `AGENTS.md` (create project rules)
- `docs/01_Master_Architecture.md`

**Database Changes:** None.

**Backend Changes:**
- Create FastAPI app with health check endpoint `GET /`
- Configure CORS middleware (localhost:5173 for frontend dev)
- Basic exception handler
- Pydantic settings for environment variables (DATABASE_URL for the SQLite file, AI_API_KEY, etc.)

**Frontend Changes:** None beyond scaffolding.

**API Endpoints:**
- `GET /` — Health check (returns `{"status": "ok"}`)

**Acceptance Criteria:**
- `python scripts/dev.py` (or `uvicorn` + `npm run dev`) starts backend and frontend with no Docker required
- Backend starts without errors on port 8000
- Frontend starts without errors on port 5173
- `GET /` returns `{"status": "ok"}`
- `pyproject.toml` includes FastAPI, Uvicorn, SQLModel, SQLAlchemy, aiosqlite, pytest, pytest-asyncio, ruff

**Manual Testing:**
1. Run the dev script (backend + frontend)
2. Open `http://127.0.0.1:8000/` → see `{"status": "ok"}`
3. Open `http://127.0.0.1:8000/docs` → see FastAPI Swagger UI
4. Open `http://localhost:5173/` → see Vite dev server page

**Definition of Done:** Local dev setup starts backend and frontend without Docker, each renders its initial page, health check responds.

**Estimated Time:** 30 minutes

**Dependencies:** None.

---

### Sprint 2 — Database Schema & Models

**Objective:** Create all SQLModel models, database indexes, and Alembic migration scaffolding for the full MVP schema.

**Files Created:**
- `backend/app/db/__init__.py`
- `backend/app/db/connection.py`
- `backend/app/db/models.py`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/001_initial_migration.py`

**Files Modified:**
- `backend/app/main.py` (add DB initialization on startup)

**Database Changes:**
- Create all tables per `docs/01_Master_Architecture.md` §15.1:
  - `users`, `challenges`, `challenge_daily`
  - `sessions`, `rounds`, `entries`, `ai_entries`
  - `votes`, `scores`, `humanity_scores`
  - `streaks`, `leaderboard_snapshots`, `prompt_audit`
- All indexes from `docs/02_Implementation_Guide.md` §1.2

**Backend Changes:**
- Async SQLite connection (aiosqlite) using SQLAlchemy 2.0 + SQLModel, WAL mode and `PRAGMA foreign_keys=ON` enabled
- Model definitions for all 13 tables (see §1.1 of Implementation Guide)
- `init_db()` function using Alembic
- Connection lifecycle in FastAPI startup/shutdown events

**Frontend Changes:** None.

**API Endpoints:** None.

**Acceptance Criteria:**
- `alembic upgrade head` creates all 13 tables
- All indexes are created
- `init_db()` works without errors
- `SQLModel.metadata.create_all(engine)` succeeds

**Manual Testing:**
1. Run `alembic upgrade head`
2. Connect with `sqlite3 backend/manvsmachine.db`: `.tables` → see all 13 tables (+ `alembic_version`)
3. `SELECT name FROM sqlite_master WHERE type='index';` → see all indexes listed

**Definition of Done:** All tables and indexes are created via Alembic migration, models match the schema in the Implementation Guide.

**Estimated Time:** 60 minutes

**Dependencies:** Sprint 1.

---

### Sprint 3 — Repositories

**Objective:** Implement all six repositories with full CRUD + query methods as specified in the Implementation Guide.

**Files Created:**
- `backend/app/repositories/__init__.py`
- `backend/app/repositories/base.py`
- `backend/app/repositories/user.py`
- `backend/app/repositories/challenge.py`
- `backend/app/repositories/session.py`
- `backend/app/repositories/voting.py`
- `backend/app/repositories/scoring.py`
- `backend/app/repositories/prompt_audit.py`

**Files Modified:**
- `backend/app/db/models.py` (import models into `__all__`)

**Database Changes:** None (tables already exist from Sprint 2).

**Backend Changes:**
- `UserRepository`: `create_guest`, `get_by_id`, `get_by_guest_id`, `update_rating`, `update_display_name`, `get_leaderboard`
- `ChallengeRepository`: `get_by_id`, `get_daily`, `create`, `get_all_ids`, `increment_daily_usage`
- `SessionRepository`: `create`, `get`, `update_state`, `complete`, `get_user_sessions`
- `VotingRepository`: `create_vote`, `get_votes_for_round`, `record_reveal`, `get_entries_anonymized`
- `ScoringRepository`: `create_score`, `get_daily_scores`, `get_user_rating`, `update_streak`
- `PromptAuditRepository`: `record`, `get_by_challenge`, `get_versions`
- Base repository with async session management

**Frontend Changes:** None.

**API Endpoints:** None.

**Acceptance Criteria:**
- All repository methods return correct pydantic models
- `get_leaderboard()` returns ranked users by detection_rating
- `get_daily()` returns today's challenge deterministically
- `get_all_ids()` returns all challenge IDs
- `get_entries_anonymized()` returns `{"A": "...", "B": "..."}` with randomized assignment
- All methods handle non-existent IDs gracefully

**Manual Testing:**
1. Run a Python script that uses each repository
2. Create a guest user → verify persisted
3. Query leaderboard → verify returns users
4. Get daily challenge → verify deterministic by date

**Definition of Done:** All 6 repositories implemented and verified, tests written for each method.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 2.

---

### Sprint 4 — API Scaffolding & Auth

**Objective:** Implement FastAPI routers with CORS, JWT auth, and the auth endpoints (guest, login, register).

**Files Created:**
- `backend/app/core/__init__.py`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/core/exceptions.py`
- `backend/app/core/state.py` (in-process ephemeral state store)
- `backend/app/api/__init__.py`
- `backend/app/api/v1/__init__.py`
- `backend/app/api/v1/user.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/user.py`

**Files Modified:**
- `backend/app/main.py` (include API routers, middleware)

**Database Changes:** None.

**Backend Changes:**
- Pydantic settings (`Settings` class) loading from environment
- JWT token generation/validation (`create_access_token`, `decode_token`)
- Password hashing with `passlib`
- Guest user creation endpoint
- Auth dependency for protected endpoints
- In-process ephemeral state store (replaces Redis)

**Frontend Changes:** None.

**API Endpoints:**
- `POST /api/v1/auth/guest` — Create/get guest session
- `POST /api/v1/auth/login` — Login with email/password
- `POST /api/v1/auth/register` — Register new account

**Acceptance Criteria:**
- Guest endpoint returns `user_id`, `guest_id`, `display_name`, `token`
- JWT tokens are generated and can be decoded
- Protected endpoints reject requests without valid token
- State store initializes on startup

**Manual Testing:**
1. Start backend
2. POST to `/api/v1/auth/guest` → verify response with token
3. Use token to call a protected endpoint → verify 200
4. Call without token → verify 401

**Definition of Done:** Auth endpoints work, JWT tokens issued and verified, state store initializes, all auth tests pass.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 3.

---

## Phase 1: Challenge Engine (Sprints 5-7)

### Sprint 5 — Challenge Library & Data Files

**Objective:** Create all 25 challenge definition JSON files from the Micro Challenge Library, plus sample stub entries for testing.

**Files Created:**
- `backend/app/data/challenge_library/challenge_slogan_01.json`
- `backend/app/data/challenge_library/challenge_caption_02.json`
- (23 more challenge files matching `docs/05_Micro_Challenge_Library.md`)
- `backend/app/data/stub_entries/challenge_slogan_01.json`
- `backend/app/data/stub_entries/challenge_caption_02.json`
- (sample stub entries for 5 challenges)
- `backend/app/data/ai_prompts/v1.0.json`

**Files Modified:** None.

**Database Changes:** None.

**Backend Changes:**
- Challenge JSON files matching the schema in `docs/02_Implementation_Guide.md` §10.1
- Stub entry pools for each challenge (10-20 human-quality entries)
- Prompt template v1.0 with system prompt, user template, instructions, humanity_guidance

**Frontend Changes:** None.

**API Endpoints:** None (challenge loading happens in Sprint 6).

**Acceptance Criteria:**
- All 25 challenge JSON files are valid and match the schema
- Each challenge has a corresponding stub entry pool
- `v1.0.json` prompt template is well-formed
- At least 5 stub entry pools contain 10+ entries each

**Manual Testing:**
1. Validate each JSON file against the schema
2. Verify challenge IDs match the Micro Challenge Library doc
3. Check stub entries are human-quality

**Definition of Done:** All 25 challenge definitions and stub entry pools are created and validated.

**Estimated Time:** 60 minutes

**Dependencies:** Sprint 2.

---

### Sprint 6 — Challenge Engine & Constraint Engine

**Objective:** Implement the ChallengeService, ConstraintEngine, ScoringEngine, and input validators.

**Files Created:**
- `backend/app/services/__init__.py`
- `backend/app/services/challenge_service.py`
- `backend/app/services/constraint_engine.py`
- `backend/app/services/scoring_engine.py`
- `backend/app/services/input_validator.py`
- `backend/app/schemas/challenge.py`
- `backend/tests/test_challenge_engine.py`

**Files Modified:**
- `backend/app/main.py` (include challenge router — added in Sprint 7)

**Database Changes:** None.

**Backend Changes:**
- `ChallengeService`: `get_challenge`, `get_daily_challenge`, `apply_constraints`, `validate_input`, `generate_time_limit`, `rotate_daily_challenge`, `get_challenge_pool`
- `ConstraintEngine`: `validate(entry, constraints) -> ConstraintResult` with hard/soft violation distinction
- `ScoringEngine`: `calculate_score(vote_correct, time_remaining, time_limit, streak, challenge) -> int`
- `InputValidator`: validates `text_single_line` and `text_multi_line` input types
- Constraint types: `max_words`, `max_characters`, `must_rhyme`, `no_adjectives`, `must_include_theme`, `exactly_n_emojis`, `no_letter_e`, `one_sentence_only`

**Frontend Changes:** None.

**API Endpoints:** None (endpoints added in Sprint 7).

**Acceptance Criteria:**
- `get_challenge("challenge_slogan_01")` returns full ChallengeDefinition
- `apply_constraints()` correctly identifies hard violations (blocks submission) and soft violations (tracks only)
- `validate_input()` rejects empty entries and enforces input type rules
- `generate_time_limit()` returns base time from challenge, adjusted by difficulty
- `rotate_daily_challenge()` is deterministic by date
- `ScoringEngine.calculate_score()` matches the formula in §12.5 of Master Architecture

**Manual Testing:**
1. Load a challenge definition
2. Validate a valid entry → no hard violations
3. Validate a 6-word entry against max 5 words → hard violation
4. Run scoring with known inputs → verify formula
5. Test daily rotation twice with same date → same result

**Definition of Done:** Challenge engine, constraint engine, scoring engine, and input validators are fully implemented and tested.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 5, Sprint 3.

---

### Sprint 7 — Challenge & Session API Endpoints

**Objective:** Implement the Challenge and Session REST API endpoints and session start/next-round logic.

**Files Created:**
- `backend/app/api/v1/challenges.py`
- `backend/app/api/v1/session.py`
- `backend/app/schemas/session.py`

**Files Modified:**
- `backend/app/main.py` (include challenge + session routers)

**Database Changes:** None.

**Backend Changes:**
- `GET /challenges/daily` — returns today's challenge + starts a daily session
- `GET /challenges/{id}` — returns full challenge definition
- `POST /challenges/validate` — validates an entry before submission
- `POST /session/start` — creates a session with 3 challenges
- `GET /session/{id}` — returns session state
- `GET /session/{id}/summary` — returns session summary

**Frontend Changes:** None.

**API Endpoints:**
- `GET /api/v1/challenges/daily`
- `GET /api/v1/challenges/{challenge_id}`
- `POST /api/v1/challenges/validate`
- `POST /api/v1/session/start`
- `GET /api/v1/session/{session_id}`
- `GET /api/v1/session/{session_id}/summary`

**Acceptance Criteria:**
- `/challenges/daily` returns a challenge and assigns it to a session (creates if none active)
- `/session/start` creates a session with 3 challenges and returns `session_id` + `next_challenge`
- `/session/{id}` returns session state (current_round, state, etc.)
- Validation endpoint returns validity, violations, word count, character count
- All endpoints return 200/201 with correct JSON schema

**Manual Testing:**
1. POST to `/session/start` with daily type → verify session created
2. GET `/challenges/daily` → verify challenge returned
3. POST to `/challenges/validate` with valid entry → verify `{"valid": true}`
4. GET `/session/{id}` → verify state

**Definition of Done:** All challenge and session API endpoints are implemented, return correct schemas, and pass tests.

**Estimated Time:** 60 minutes

**Dependencies:** Sprint 6, Sprint 4.

---

## Phase 2: AI Layer (Sprints 8-10)

### Sprint 8 — Content Filter & Prompt Audit

**Objective:** Implement the ContentFilter for prompt injection protection and the PromptAuditService for prompt versioning and audit trail.

**Files Created:**
- `backend/app/services/content_filter.py`
- `backend/app/services/prompt_audit_service.py`
- `backend/app/schemas/prompt.py`
- `backend/tests/test_content_filter.py`
- `backend/tests/test_prompt_audit.py`

**Files Modified:** None.

**Database Changes:** None.

**Backend Changes:**
- `ContentFilter`: `sanitize_ai_response`, `check_prompt_injection`, `strip_system_prompt_leakage`, `validate_no_meta_mentions`
- Meta-mention patterns: "as an AI", "I'm an AI", "as a language model", etc.
- Injection patterns: "ignore all previous instructions", "new instructions:", etc.
- `PromptAuditService`: `get_prompt_template`, `record_usage`, `list_versions`
- Loads prompt templates from `app/data/ai_prompts/`

**Frontend Changes:** None.

**API Endpoints:** None (internal services).

**Acceptance Criteria:**
- `sanitize_ai_response()` strips meta-mentions and truncates to 500 chars
- `check_prompt_injection()` detects and flags injection patterns
- `validate_no_meta_mentions()` returns False for responses containing "as an AI"
- `validate_no_meta_mentions()` returns True for clean human-like responses
- Prompt template v1.0 is loaded correctly
- `record_usage()` stores prompt + response in `prompt_audit` table

**Manual Testing:**
1. Run `sanitize_ai_response("As an AI, I think...")` → verify meta-mention stripped
2. Run `check_prompt_injection("ignore all previous instructions")` → verify flagged
3. Load prompt template v1.0 → verify system_prompt, user_template present
4. Call `record_usage()` → verify entry in prompt_audit table

**Definition of Done:** ContentFilter and PromptAuditService are fully implemented, all security checks work, tests pass.

**Estimated Time:** 60 minutes

**Dependencies:** Sprint 5 (prompt template), Sprint 3 (PromptAuditRepository).

---

### Sprint 9 — AI Provider Abstraction

**Objective:** Implement the AIProvider base interface and three concrete providers: OpenAI, Anthropic, and Stub.

**Files Created:**
- `backend/app/services/ai/providers/__init__.py`
- `backend/app/services/ai/providers/base.py`
- `backend/app/services/ai/providers/openai_provider.py`
- `backend/app/services/ai/providers/anthropic_provider.py`
- `backend/app/services/ai/providers/stub_provider.py`
- `backend/app/services/ai/__init__.py`
- `backend/tests/test_ai_providers.py`

**Files Modified:** None.

**Database Changes:** None.

**Backend Changes:**
- `AIProvider` ABC: `generate`, `is_available`, `get_model_name`, `get_provider_name`
- `OpenAIProvider`: calls `https://api.openai.com/v1/chat/completions`, default model `gpt-4o-mini`
- `AnthropicProvider`: calls `https://api.anthropic.com/v1/messages`, default model `claude-3-haiku-20240307`
- `StubProvider`: loads from `app/data/stub_entries/{challenge_id}.json`, hashes prompt to select deterministically
- Provider selection: OpenAI → Anthropic → Stub fallback chain

**Frontend Changes:** None.

**API Endpoints:** None.

**Acceptance Criteria:**
- `OpenAIProvider.is_available()` returns True when API key is set
- `AnthropicProvider.is_available()` returns True when API key is set
- `StubProvider.is_available()` always returns True
- StubProvider returns a different entry each time from the pool (deterministic by prompt hash)
- Provider selection correctly falls through the chain

**Manual Testing:**
1. With no API keys: `select_provider()` returns StubProvider
2. StubProvider.generate() with a challenge → returns an entry from the pool
3. Verify same prompt → same response (deterministic)

**Definition of Done:** All three providers implemented and tested, StubProvider works without API keys.

**Estimated Time:** 60 minutes

**Dependencies:** Sprint 5 (stub entries), Sprint 8 (content filter integration point).

---

### Sprint 10 — AIService & Prompt Pipeline

**Objective:** Implement the AIService that orchestrates prompt construction, provider selection, fallback, sanitization, and audit recording.

**Files Created:**
- `backend/app/services/ai_service.py`
- `backend/app/api/v1/voting.py` (partial — entry submission endpoint)
- `backend/app/schemas/voting.py`
- `backend/tests/test_ai_service.py`

**Files Modified:**
- `backend/app/main.py` (include voting router)

**Database Changes:** None.

**Backend Changes:**
- `AIService`: `generate_entry`, `build_prompt`, `select_provider`, `sanitize_response`, `record_prompt`
- `build_prompt()`: constructs the full prompt from challenge definition + prompt template
- Fallback logic: try OpenAI, if fails try Anthropic, if fails use Stub
- Sanitization: pass all provider responses through ContentFilter
- Audit: record every prompt + response via PromptAuditService
- `POST /api/v1/voting/submit-entry` — submits a human entry and triggers AI generation

**Frontend Changes:** None.

**API Endpoints:**
- `POST /api/v1/voting/submit-entry` — Human entry submission + AI generation trigger

**Acceptance Criteria:**
- `build_prompt()` correctly formats the challenge prompt with constraints
- `select_provider()` follows the fallback chain
- AI response is sanitized before storage (no meta-mentions)
- Prompt + response is recorded in `prompt_audit` table
- `generate_entry()` returns a valid entry string

**Manual Testing:**
1. Call `build_prompt()` with a challenge → verify formatted correctly
2. Call `generate_entry()` with StubProvider → verify sanitized response
3. Check `prompt_audit` table → verify record exists
4. Submit entry via API → verify AI entry generated and stored

**Definition of Done:** AIService fully orchestrates AI entry generation with sanitization and audit trail. All AI service tests pass.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 9 (providers), Sprint 8 (content filter, prompt audit), Sprint 6 (challenge service).

---

## Phase 3: Voting, Scoring & Session (Sprints 11-14)

### Sprint 11 — Voting Service

**Objective:** Implement the VotingService for anonymous A/B entry presentation and vote processing.

**Files Created:**
- `backend/app/services/voting_service.py`
- `backend/app/services/humanity_scoring.py`
- `backend/tests/test_voting.py`

**Files Modified:**
- `backend/app/api/v1/voting.py` (add vote endpoint)
- `backend/app/repositories/voting.py` (add methods if needed)

**Database Changes:** None.

**Backend Changes:**
- `VotingService`: `present_entries` (randomize A/B), `process_vote`, `reveal` (determine human/AI, generate explanation)
- Humanity scoring: retroactively based on player guesses (percentage who guessed human)
- `POST /api/v1/voting/vote` — submits a player's vote and triggers reveal

**Frontend Changes:** None.

**API Endpoints:**
- `POST /api/v1/voting/vote` — Vote on which entry is AI

**Acceptance Criteria:**
- `present_entries()` randomizes A/B assignment consistently (seeded)
- `process_vote()` records the vote and determines if reveal can proceed
- `reveal()` correctly identifies which entry was human vs AI
- Humanity score is 0-100 based on player guess accuracy
- A/B randomization is reproducible (same seed → same assignment)

**Manual Testing:**
1. Call `present_entries()` twice with same round → verify same A/B assignment
2. Call `present_entries()` with different rounds → verify different assignments (statistical)
3. Submit a vote → verify reveal triggers with correct attribution

**Definition of Done:** Voting service handles A/B randomization, vote processing, and reveal generation. Tests pass.

**Estimated Time:** 60 minutes

**Dependencies:** Sprint 10, Sprint 3 (VotingRepository).

---

### Sprint 12 — Scoring Service

**Objective:** Implement the ScoringService for round scoring, ELO-style Detection Rating updates, humanity scoring, and streak tracking.

**Files Created:**
- `backend/app/services/scoring_service.py`
- `backend/app/services/leaderboard_service.py`
- `backend/tests/test_scoring.py`

**Files Modified:**
- `backend/app/api/v1/scoring.py` (create)
- `backend/app/api/v1/leaderboard.py` (create)
- `backend/app/main.py` (include routers)

**Database Changes:** None.

**Backend Changes:**
- `ScoringService`: `calculate_round_score`, `update_detection_rating`, `update_humanity_score`, `update_streak`, `get_current_streak`
- ELO formula: adjusted based on vote correctness and AI humanity score
- Streak logic: correct guesses increment streak, wrong guesses reset
- `ScoringEngine` integration from Sprint 6
- `LeaderboardService`: `get_daily_leaderboard`, `get_all_time_leaderboard`, `generate_snapshot`

**Frontend Changes:** None.

**API Endpoints:**
- `GET /api/v1/leaderboard/daily`
- `GET /api/v1/leaderboard/all-time`

**Acceptance Criteria:**
- `calculate_round_score()` uses the formula from §12.5 (base + time_bonus + streak_bonus)
- `update_detection_rating()` applies ELO: correct guess → +rating, wrong → -rating
- `update_humanity_score()` computes correct percentage from votes
- `update_streak()` correctly tracks daily and correct-guess streaks
- Leaderboard endpoints return ranked results with scores/ratings

**Manual Testing:**
1. Call `calculate_round_score(True, 5, 15, 2, challenge)` → verify score = 100 + time_bonus + streak_bonus
2. Call `update_detection_rating()` with correct guess → verify rating increases
3. GET `/leaderboard/daily` → verify ranked results

**Definition of Done:** Scoring and leaderboard services are fully implemented, ELO math verified, leaderboard endpoints return correct data.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 11, Sprint 6 (ScoringEngine), Sprint 3 (ScoringRepository).

---

### Sprint 13 — Session Service & State Machine

**Objective:** Implement the SessionService with the round state machine and session orchestration.

**Files Created:**
- `backend/app/services/session_service.py`
- `backend/tests/test_session.py`

**Files Modified:**
- `backend/app/api/v1/session.py` (add session endpoints if needed)

**Database Changes:** None.

**Backend Changes:**
- `SessionService`: `start_session`, `next_round`, `transition_state`, `get_session_summary`
- State machine: `IDLE → WRITING → REVEAL_AI → VOTING → SCORE → RESULT → [next round or end]`
- Round lifecycle: assigns challenge, waits for entry, generates AI entry, presents for voting, processes vote, reveals, scores
- Session orchestration: 3 rounds, then session summary

**Frontend Changes:** None.

**API Endpoints:**
- (Session endpoints already created in Sprint 7; this sprint implements backend logic)

**Acceptance Criteria:**
- `start_session()` creates a session with 3 challenges
- `transition_state()` correctly moves between states and validates transitions
- `next_round()` fetches the next challenge and resets state
- `get_session_summary()` returns total score, accuracy, per-round breakdown
- State machine rejects invalid transitions (e.g., WRITING → SCORE without VOTE)

**Manual Testing:**
1. Call `start_session()` → verify 3 rounds queued
2. Transition through WRITING → REVEAL_AI → VOTING → SCORE → RESULT manually
3. Verify each transition updates the `rounds.state` column
4. Call `get_session_summary()` after 3 rounds → verify complete summary

**Definition of Done:** Session state machine enforces correct transitions, session summary is accurate, tests pass.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 12, Sprint 11, Sprint 10.

---

### Sprint 14 — WebSocket Layer

**Objective:** Implement the WebSocket manager, connection handling, and event broadcasting for real-time session flow.

**Files Created:**
- `backend/app/websocket/__init__.py`
- `backend/app/websocket/manager.py`
- `backend/app/websocket/handlers.py`
- `backend/tests/test_websocket.py`

**Files Modified:**
- `backend/app/main.py` (add WebSocket route)

**Database Changes:** None (uses in-process state for ephemeral data).

**Backend Changes:**
- `WebSocketManager`: connection lifecycle, dispatch via in-process pub/sub
- WebSocket route: `/ws/session/{session_id}?token=...`
- Auth: validate JWT from query parameter
- Event handlers for: `SUBMIT_ENTRY`, `VOTE`, `PING`
- Server events broadcast: `SESSION_STARTED`, `ROUND_START`, `AI_RESPONSE_READY`, `REVEAL`, `ROUND_SCORED`, `SESSION_END`, `ERROR`, `PONG`
- In-process pub/sub topic per session

**Frontend Changes:** None.

**API Endpoints:** None (WebSocket only).

**WebSocket Events:**
- Client → Server: `SUBMIT_ENTRY`, `VOTE`, `PING`
- Server → Client: `SESSION_STARTED`, `ROUND_START`, `AI_RESPONSE_READY`, `REVEAL`, `ROUND_SCORED`, `SESSION_END`, `ERROR`, `PONG`

**Acceptance Criteria:**
- WebSocket connection authenticates via JWT query param
- `SUBMIT_ENTRY` triggers AI generation and pushes `AI_RESPONSE_READY`
- `VOTE` triggers reveal and scoring, pushes `REVEAL` + `ROUND_SCORED`
- Invalid token → connection rejected
- Connection failure → client can rejoin (state in SQLite)

**Manual Testing:**
1. Connect WebSocket with valid token → verify `SESSION_STARTED` received
2. Send `SUBMIT_ENTRY` → verify `AI_RESPONSE_READY` with anonymized entries
3. Send `VOTE` → verify `REVEAL` with correct attribution
4. Verify `SESSION_END` after 3 rounds
5. Connect with invalid token → verify rejected

**Definition of Done:** WebSocket layer handles full round flow in real-time, auth works, pub/sub dispatch is correct.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 13 (session service), Sprint 11 (voting), Sprint 12 (scoring), Sprint 4 (state store, auth).

---

## Phase 4: Frontend Foundation (Sprints 15-17)

### Sprint 15 — Frontend Scaffolding

**Objective:** Set up the React + TypeScript + Vite + shadcn/ui + Tailwind CSS project with routing and basic page structure.

**Files Created:**
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/package.json`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/app.tsx`
- `frontend/src/routes/index.tsx`
- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/Auth.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/styles/globals.css`
- `frontend/.eslintrc.js`
- `frontend/.prettierrc`

**Files Modified:** None.

**Database Changes:** None.

**Backend Changes:** None.

**Frontend Changes:**
- Vite + React + TypeScript project
- shadcn/ui base components installed
- Tailwind CSS configured
- React Router v6 with 7 routes (Home, Session, Challenge, Leaderboard, Profile, Auth, Settings)
- Axios instance (`src/api/client.ts`) configured with base URL
- Basic layout with navigation

**API Endpoints:** None (will consume in later sprints).

**Acceptance Criteria:**
- `npm install` succeeds in frontend/
- `npm run dev` starts Vite on port 5173
- All 7 pages render (even if just placeholders)
- React Router navigates correctly between routes
- TypeScript compiles without errors

**Manual Testing:**
1. Run `cd frontend && npm install`
2. Run `npm run dev`
3. Navigate to each route → verify page renders
4. Verify TypeScript compiles: `npx tsc --noEmit`

**Definition of Done:** Frontend project is fully scaffolded with all routes and pages, TypeScript compiles clean.

**Estimated Time:** 60 minutes

**Dependencies:** Sprint 1 (shared types reference).

---

### Sprint 16 — API Client & Shared Types

**Objective:** Create the Axios API client with typed endpoints and shared TypeScript types matching the backend schemas.

**Files Created:**
- `frontend/src/api/client.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/api/challenges.ts`
- `frontend/src/api/session.ts`
- `frontend/src/api/voting.ts`
- `frontend/src/api/leaderboard.ts`
- `frontend/src/api/profile.ts`
- `frontend/src/api/share.ts`
- `frontend/src/types/index.ts`
- `frontend/src/types/challenge.ts`
- `frontend/src/types/session.ts`
- `frontend/src/types/voting.ts`
- `frontend/src/types/user.ts`

**Files Modified:**
- `frontend/src/app.tsx` (wrap with AuthProvider)

**Database Changes:** None.

**Backend Changes:** None.

**Frontend Changes:**
- Axios instance with base URL `http://127.0.0.1:8000/api/v1`
- JWT token interceptor (attach to Authorization header)
- Typed API call functions for all 6 resource groups
- TypeScript interfaces matching all backend pydantic schemas
- `ChallengeDefinition`, `Session`, `Round`, `ChallengeBrief`, `VoteResult`, `LeaderboardEntry`, `UserProfile`, `SessionSummary`

**API Endpoints:**
- `POST /api/v1/auth/guest` (consumed)
- `GET /api/v1/challenges/daily` (consumed)
- `GET /api/v1/challenges/{id}` (consumed)
- `POST /api/v1/session/start` (consumed)
- `GET /api/v1/session/{id}` (consumed)
- `GET /api/v1/session/{id}/summary` (consumed)
- `GET /api/v1/leaderboard/daily` (consumed)
- `GET /api/v1/leaderboard/all-time` (consumed)
- `GET /api/v1/profile` (consumed)
- `POST /api/v1/share/result` (consumed)

**Acceptance Criteria:**
- All API client methods have correct return types
- Types match backend schemas (ChallengeDefinition, Session, etc.)
- Axios interceptors attach JWT token
- Error handling for 401, 404, 500 responses

**Manual Testing:**
1. Call api client method for each endpoint → verify TypeScript compiles
2. Verify types match backend pydantic schemas

**Definition of Done:** API client is fully typed and matches all backend schemas. TypeScript compiles without errors.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 15, Sprint 4 (backend auth).

---

### Sprint 17 — Auth Context & Guest Mode

**Objective:** Implement the AuthContext and useAuth hook for guest login, email/password auth, and JWT token management.

**Files Created:**
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/lib/utils.ts`

**Files Modified:**
- `frontend/src/app.tsx` (wrap with AuthProvider)
- `frontend/src/routes/index.tsx` (add Auth route guard)

**Database Changes:** None.

**Backend Changes:** None.

**Frontend Changes:**
- `AuthContext`: provides `user`, `isAuthenticated`, `isGuest`, `login`, `register`, `loginAsGuest`, `logout`
- `useAuth` hook: wraps context with convenience methods
- JWT token stored in localStorage
- Guest mode: auto-login as guest on first visit, persist guest_id
- Auto-refresh: check token validity on app load

**API Endpoints:**
- `POST /api/v1/auth/guest` (consumed)
- `POST /api/v1/auth/login` (consumed)
- `POST /api/v1/auth/register` (consumed)

**Acceptance Criteria:**
- First visit → auto guest login, token stored in localStorage
- Page refresh → token restored, user still authenticated
- Login with email/password → token updated
- Register creates new account → token issued
- Logout clears token and localStorage

**Manual Testing:**
1. Open app in incognito → verify guest login occurs
2. Refresh page → verify still logged in as guest
3. Register with email → verify account created
4. Logout → verify token cleared, redirected to auth page

**Definition of Done:** Auth context handles guest and registered users, JWT tokens are managed securely, tests pass.

**Estimated Time:** 60 minutes

**Dependencies:** Sprint 16, Sprint 4, Sprint 15.

---

## Phase 5: Game UI (Sprints 18-22)

### Sprint 18 — ChallengeView, Timer & EntryInput

**Objective:** Implement the ChallengeView, Timer, and EntryInput components that display the challenge prompt and capture the human's entry.

**Files Created:**
- `frontend/src/components/ChallengeView.tsx`
- `frontend/src/components/Timer.tsx`
- `frontend/src/components/EntryInput.tsx`
- `frontend/src/components/StreakBadge.tsx`
- `frontend/src/components/RatingDisplay.tsx`
- `frontend/src/hooks/useTimer.ts`
- `frontend/src/hooks/useChallenges.ts`

**Files Modified:**
- `frontend/src/pages/Challenge.tsx` (basic wiring)
- `frontend/src/contexts/SessionContext.tsx` (create placeholder)

**Database Changes:** None.

**Backend Changes:** None.

**Frontend Changes:**
- `ChallengeView`: displays prompt, constraints, time limit, difficulty badge
- `Timer`: countdown with urgency color shift (green → yellow → red at 5s)
- `EntryInput`: text input with live word/character count, constraint validation feedback
- `StreakBadge`: daily streak counter with fire icon
- `RatingDisplay`: Detection Rating with change indicator
- `useTimer` hook: countdown logic with urgency states, auto-submit at 0

**API Endpoints:**
- `GET /api/v1/challenges/{id}` (consumed)
- `POST /api/v1/challenges/validate` (consumed)

**Acceptance Criteria:**
- Timer counts down from challenge's time_limit_seconds
- Timer turns red when 5 seconds remain
- EntryInput enforces max_words/max_characters constraints
- Live word/character count updates as user types
- Constraint violations show error messages
- Submit button disables when constraints are violated

**Manual Testing:**
1. Load a challenge → verify prompt + constraints display
2. Start timer → verify countdown
3. Type a 6-word entry with max 5 words → verify error shown
4. Type valid entry → verify submit enabled

**Definition of Done:** ChallengeView, Timer, EntryInput, StreakBadge, RatingDisplay are all functional with proper constraint validation and urgency states.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 15, Sprint 16, Sprint 8 (challenge engine).

---

### Sprint 19 — Voting Screen & Voting Context

**Objective:** Implement the VotingScreen component and VotingContext that display anonymized A/B entries and capture the player's vote.

**Files Created:**
- `frontend/src/components/VotingScreen.tsx`
- `frontend/src/contexts/VotingContext.tsx`
- `frontend/src/contexts/ScoringContext.tsx`
- `frontend/src/hooks/useVoting.ts`
- `frontend/src/websocket/client.ts`
- `frontend/src/websocket/events.ts`

**Files Modified:**
- `frontend/src/app.tsx` (add VotingProvider and ScoringProvider)
- `frontend/src/routes/index.tsx` (add Session route)

**Database Changes:** None.

**Backend Changes:** None.

**Frontend Changes:**
- `VotingContext`: provides `entries`, `humanWas`, `humanityScores`, `explanation`, `vote`, `isVoting`
- `VotingScreen`: displays Entry A and Entry B, vote buttons, hides player's own entry origin
- WebSocket client wrapper for connection management
- Typed WebSocket events matching `docs/01_Master_Architecture.md` §16.1
- `useVoting` hook: connects to WebSocket, listens for `AI_RESPONSE_READY`, submits `VOTE_SUBMITTED`

**WebSocket Events:**
- Client → Server: `SUBMIT_ENTRY`, `VOTE_SUBMITTED`, `PING`
- Server → Client: `SESSION_STARTED`, `ROUND_START`, `AI_RESPONSE_READY`, `REVEAL`, `ROUND_SCORED`, `SESSION_END`, `ERROR`, `PONG`

**Acceptance Criteria:**
- VotingScreen shows two entries labeled A and B
- Player cannot tell which entry is theirs
- Vote buttons send `VOTE_SUBMITTED` via WebSocket
- Loading state shown while waiting for AI entry
- 10-second voting window with soft nudge after expiry

**Manual Testing:**
1. Connect to a session via WebSocket → receive `ROUND_START`
2. View VotingScreen → verify entries displayed as A/B
3. Click a vote button → verify `VOTE_SUBMITTED` sent
4. Verify no indication of which entry is the player's

**Definition of Done:** VotingScreen displays anonymized entries, WebSocket connection sends/receives correct events, player cannot identify their own entry.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 18, Sprint 17, Sprint 14 (WebSocket backend), Sprint 16.

---

### Sprint 20 — Reveal Screen & Score Animation

**Objective:** Implement the RevealScreen and ScoreAnimation components that show the reveal with humanity scores and animate the player's score.

**Files Created:**
- `frontend/src/components/RevealScreen.tsx`
- `frontend/src/components/ScoreAnimation.tsx`
- `frontend/src/components/SessionSummary.tsx`
- `frontend/src/hooks/useScoring.ts`
- `frontend/src/websocket/hooks.ts` (useRoundState, useSessionEvents)

**Files Modified:**
- `frontend/src/contexts/VotingContext.tsx` (add reveal state)
- `frontend/src/contexts/ScoringContext.tsx` (add score state)

**Database Changes:** None.

**Backend Changes:** None.

**Frontend Changes:**
- `RevealScreen`: flip animation, reveals which entry was human/AI, humanity scores (0-100), explanation text
- `ScoreAnimation`: animated counter showing score breakdown (base + time_bonus + streak_bonus)
- `SessionSummary`: end-of-session stats, share button
- `useRoundState` hook: subscribes to ROUND_START, AI_RESPONSE_READY, REVEAL, ROUND_SCORED
- `useSessionEvents` hook: subscribes to SESSION_STARTED, SESSION_END

**WebSocket Events:**
- Client receives: `REVEAL` (with `humanWas`, `humanityHuman`, `humanityAI`, `explanation`), `ROUND_SCORED` (with `score`, `ratingChange`, `streakUpdate`)

**Acceptance Criteria:**
- RevealScreen shows correct attribution (A=Human, B=AI or vice versa)
- Humanity scores displayed as 0-100 bars
- Explanation text shown (e.g., "The AI entry used overly formal phrasing")
- Score animation counts up from 0 to final score
- Score breakdown shows base, time_bonus, streak_bonus
- SessionSummary appears after round 3

**Manual Testing:**
1. Receive `REVEAL` event → verify correct attribution displayed
2. Verify humanity scores 0-100 bars render
3. Receive `ROUND_SCORED` → verify score animation plays
4. After 3 rounds → verify SessionSummary appears

**Definition of Done:** RevealScreen and ScoreAnimation are fully animated, WebSocket event hooks work correctly, session summary is displayed.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 19, Sprint 14.

---

### Sprint 21 — Session Flow & Session Context

**Objective:** Implement the Session page and SessionContext that orchestrate the full 3-round game loop (challenge → write → vote → reveal → score → next).

**Files Created:**
- `frontend/src/pages/Session.tsx`
- `frontend/src/contexts/SessionContext.tsx`
- `frontend/src/hooks/useSession.ts`

**Files Modified:**
- `frontend/src/routes/index.tsx` (wire Session page to /session route)
- `frontend/src/app.tsx` (add SessionProvider)

**Database Changes:** None.

**Backend Changes:** None.

**Frontend Changes:**
- `SessionContext`: provides `session`, `currentRound`, `challenge`, `gameState`, `timeRemaining`, `startSession`, `submitEntry`, `submitVote`, `nextRound`
- `gameState` values: 'idle' | 'writing' | 'reveal_ai' | 'voting' | 'score' | 'complete'
- `Session` page: full-screen component that swaps between ChallengeView+EntryInput (writing), VotingScreen (voting), RevealScreen+ScoreAnimation (score), SessionSummary (complete)
- `useSession` hook: orchestrates the full game loop via WebSocket events

**WebSocket Events:**
- Client sends: `SUBMIT_ENTRY`, `VOTE_SUBMITTED`
- Client receives: `ROUND_START`, `AI_RESPONSE_READY`, `REVEAL`, `ROUND_SCORED`, `SESSION_END`

**Acceptance Criteria:**
- Session page starts in 'writing' state with challenge prompt
- After entry submission → transitions to 'voting' state with A/B entries
- After vote → transitions to 'score' state with reveal
- After score shown → auto-proceeds to next round or session summary
- 3 rounds complete → SESSION_END → SessionSummary shown
- Timer works in 'writing' state, auto-submits at 0

**Manual Testing:**
1. Start a new session → verify first challenge loads
2. Type entry + submit → verify transition to voting
3. See A/B entries → vote → verify reveal
4. Verify score shown → verify next round starts
5. After 3 rounds → verify session summary

**Definition of Done:** Full 3-round session flow works end-to-end via WebSocket, all state transitions correct, session summary accurate.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 20, Sprint 19, Sprint 18, Sprint 14.

---

### Sprint 22 — Leaderboard & Profile Pages

**Objective:** Implement the Leaderboard and Profile pages with daily/all-time rankings and user stats.

**Files Created:**
- `frontend/src/pages/Leaderboard.tsx`
- `frontend/src/pages/Profile.tsx`
- `frontend/src/components/LeaderboardTable.tsx`
- `frontend/src/components/HumanityMeter.tsx`
- `frontend/src/hooks/useLeaderboard.ts`
- `frontend/src/api/profile.ts`

**Files Modified:**
- `frontend/src/routes/index.tsx` (add leaderboard and profile routes)
- `frontend/src/components/StreakBadge.tsx` (add to nav bar)

**Database Changes:** None.

**Backend Changes:** None.

**Frontend Changes:**
- `Leaderboard` page: tab between daily and all-time views
- `LeaderboardTable`: sortable columns (rank, name, score/rating, accuracy)
- `Profile` page: display name, detection rating, total rounds, accuracy, streaks, humanity score trend (Chart.js)
- `HumanityMeter`: 0-100 bar showing how human-like the player's entries appear
- `useLeaderboard` hook: fetches daily + all-time data
- Settings page: AI provider selection (stub/local/online)

**API Endpoints:**
- `GET /api/v1/leaderboard/daily` (consumed)
- `GET /api/v1/leaderboard/all-time` (consumed)
- `GET /api/v1/profile` (consumed)
- `PUT /api/v1/profile` (consumed)

**Acceptance Criteria:**
- Leaderboard page shows daily rankings with rank, name, score, accuracy
- Switching to all-time shows ranked by detection rating
- Profile page shows all user stats and streaks
- HumanityMeter shows 0-100 bar for recent entries
- Settings page shows AI provider options

**Manual Testing:**
1. Navigate to Leaderboard → verify daily rankings load
2. Switch to all-time → verify ratings load
3. Navigate to Profile → verify stats display
4. Verify humanity scores are shown with meters

**Definition of Done:** Leaderboard and Profile pages fully functional, all data displays correctly, Chart.js trend renders.

**Estimated Time:** 90 minutes

**Dependencies:** Sprint 15, Sprint 16, Sprint 12 (leaderboard backend).

---

## Phase 6: Integration & Polish (Sprints 23-27)

### Sprint 23 — Settings Page & Content Filter Integration

**Objective:** Implement the Settings page with AI provider selection, theme toggle, and sound controls.

**Files Created:**
- `frontend/src/pages/Settings.tsx`
- `frontend/src/components/ThemeProvider.tsx`
- `frontend/src/hooks/useSettings.ts`

**Files Modified:**
- `frontend/src/routes/index.tsx` (add settings route)
- `frontend/src/app.tsx` (add SettingsProvider)

**Database Changes:** None.

**Frontend Changes:**
- `Settings` page: AI provider dropdown (OpenAI/Anthropic/Stub), theme toggle (light/dark), sound on/off
- `ThemeProvider`: manages theme via localStorage
- `useSettings` hook: persists settings to localStorage

**Acceptance Criteria:**
- Settings page renders with all controls
- Theme toggle switches between light/dark mode
- AI provider selection persists across sessions
- Sound toggle persists

**Manual Testing:**
1. Navigate to Settings → verify all controls present
2. Toggle theme → verify persists on refresh
3. Change AI provider → verify persists
4. Toggle sound → verify persists

**Definition of Done:** Settings page functional, all settings persist, theme switch works.

**Estimated Time:** 30 minutes

**Dependencies:** Sprint 15, Sprint 17.

---

### Sprint 24 — E2E Test Flow

**Objective:** Write and verify the end-to-end test flow that exercises the full game loop with StubProvider.

**Files Created:**
- `backend/tests/conftest.py`
- `backend/tests/test_e2e.py`
- `backend/tests/fixtures/challenges/` (3 sample challenge JSONs)
- `backend/tests/fixtures/ai_responses/` (sample responses for sanitization)

**Files Modified:**
- `docs/01_Master_Architecture.md` §21 (if test approach changes)

**Database Changes:** None (uses a test SQLite database).

**Backend Changes:** None.

**Frontend Changes:** None.

**API Endpoints:** All (tested end-to-end).

**Acceptance Criteria:**
- E2E test starts backend with StubProvider
- Creates a session with 3 challenges
- WebSocket connection established
- Human entry submitted via WebSocket → AI entry generated
- Entries anonymized (A/B) → vote submitted
- Reveal shows correct attribution
- Score calculated and rating updated
- Session summary generated
- Stakeholder can play full game without real AI API keys

**Manual Testing:**
1. Run `pytest tests/test_e2e.py -v`
2. Verify all steps in the E2E flow pass
3. Verify no real AI API keys are needed (StubProvider only)

**Definition of Done:** Full E2E test passes, all 13 steps in the test flow section of the Implementation Guide work with StubProvider.

**Estimated Time:** 90 minutes

**Dependencies:** All previous sprints (full stack must be working).

---

### Sprint 25 — Share Service & Result Cards

**Objective:** Implement the ShareService for generating shareable text summaries and static image result cards.

**Files Created:**
- `backend/app/services/share_service.py`
- `backend/app/api/v1/share.py`
- `backend/app/schemas/share.py`
- `frontend/src/components/ResultCard.tsx`
- `frontend/src/components/ShareButton.tsx`
- `frontend/src/hooks/useShare.ts`

**Files Modified:**
- `backend/app/main.py` (include share router)
- `frontend/src/pages/Session.tsx` (add share button)

**Database Changes:** None.

**Backend Changes:**
- `ShareService`: `generate_share_text`, `generate_share_image` (PNG via PIL), `create_share_link`
- `POST /api/v1/share/result` — generates text + image summary

**Frontend Changes:**
- `ResultCard`: displays score, accuracy, humanity stats, "share" button
- `ShareButton`: copies text to clipboard, opens share dialog
- `useShare` hook: calls share API, handles clipboard/download

**API Endpoints:**
- `POST /api/v1/share/result`

**Acceptance Criteria:**
- Share text follows format: "I scored 275 on today's Man vs. Machine daily challenge! Can you beat my accuracy? #ManVsMachine"
- Share image (PNG) generated with score, accuracy, humanity bars
- Share link creates a viewable replay
- Frontend ShareButton copies text to clipboard and offers image download

**Manual Testing:**
1. Complete a session → click Share
2. Verify text summary generated
3. Verify image generated (PNG with stats)
4. Click "Copy" → verify clipboard has text

**Definition of Done:** ShareService generates both text and image results, frontend ShareButton works, tests pass.

**Estimated Time:** 60 minutes

**Dependencies:** Sprint 13 (session summary), Sprint 21 (session flow).

---

### Sprint 26 — Challenge Library Validation & Stub Data Load

**Objective:** Implement the migration to load all 25 challenge definitions from JSON files into the database, and verify daily rotation picks from the full pool.

**Files Created:**
- `backend/scripts/load_challenges.py`
- `backend/tests/test_challenge_data.py`

**Files Modified:**
- `backend/alembic/versions/002_load_challenges.py` (data migration)

**Database Changes:**
- Populate `challenges` table with 25 challenge definitions from JSON files
- Populate `challenge_daily` with deterministic daily challenge assignments

**Backend Changes:**
- Script to load JSON challenge definitions into the database
- Verification that all 25 challenges load correctly
- Daily rotation test (deterministic by date)

**Acceptance Criteria:**
- All 25 challenges loaded into database
- `GET /challenges/daily` returns one of the 25 deterministically by date
- `GET /challenges/{id}` returns any of the 25 with full definition
- Daily rotation doesn't repeat within a 25-day cycle

**Manual Testing:**
1. Run `python scripts/load_challenges.py`
2. Query database → verify 25 challenges loaded
3. Call `/challenges/daily` → verify returns one of the 25
4. Test multiple dates → verify different challenges (deterministic)

**Definition of Done:** All 25 challenge definitions loaded into database, daily rotation works deterministically, tests pass.

**Estimated Time:** 30 minutes

**Dependencies:** Sprint 5 (challenge library files), Sprint 7 (challenge API).

---

### Sprint 27 — Final Polish & Local Release Config

**Objective:** Add CI/CD workflow, environment configuration, a one-port local release mode, and final polish for the MVP launch. (Docker/Nginx production deployment is post-MVP — hosted phase.)

**Files Created:**
- `.github/workflows/ci.yml`
- `backend/scripts/run.sh`
- `frontend/scripts/build.sh`
- `README.md` (quickstart: install, run, play)

**Files Modified:**
- `backend/app/main.py` (mount built frontend static files)

**Database Changes:** None.

**Backend Changes:**
- Static file mount so the FastAPI app serves the built frontend in release mode
- CI/CD workflow: lint (ruff, mypy) + tests + frontend typecheck/build on push

**Frontend Changes:**
- Production build config
- Environment variable handling

**Acceptance Criteria:**
- Fresh-checkout quickstart works: install deps, run dev script, play in browser with no Docker
- GitHub Actions CI runs on every push: lint, test, build
- `npm run build` output is served by the FastAPI backend on a single port
- All tests pass in CI

**Manual Testing:**
1. Follow the README quickstart on a clean checkout → verify the game runs locally
2. Push to GitHub → verify CI runs and passes
3. Build the frontend and serve via backend → verify single-port play (API + WebSocket + UI)

**Definition of Done:** CI passes, quickstart works on a clean checkout, MVP is playable locally without Docker.

**Estimated Time:** 60 minutes

**Dependencies:** All previous sprints.

---

## Phase 7: Documentation (Sprint 28)

### Sprint 28 — Documentation Finalization & Changelog

**Objective:** Update all documentation files with final state, changelog entries, and cross-references.

**Files Created:** None.

**Files Modified:**
- `docs/01_Master_Architecture.md` (§22 Changelog — add sprint summaries)
- `docs/02_Implementation_Guide.md` (cross-reference sprints)
- `docs/03_Sprint_Plan.md` (add per-sprint changelog entries)
- `docs/04_Game_Design_Document.md` (update if any scope changes)
- `docs/05_Micro_Challenge_Library.md` (update if challenge IDs changed)
- `AGENTS.md` (update if project rules changed)

**Database Changes:** None.

**Backend Changes:** None.

**Frontend Changes:** None.

**Acceptance Criteria:**
- All docs have final version numbers and status updates
- Changelog entries added for each completed sprint
- Cross-references between docs are accurate
- AGENTS.md reflects final project rules

**Manual Testing:**
1. Read each doc → verify accuracy against implementation
2. Verify all cross-references resolve
3. Verify AGENTS.md rules match actual architecture

**Definition of Done:** All documentation is complete, accurate, and cross-referenced.

**Estimated Time:** 60 minutes

**Dependencies:** All previous sprints complete.

---

## Appendix: Sprint Dependency Graph

```
Sprint 1  (Scaffolding)
  ├── Sprint 2  (DB Schema)          [depends on 1]
  │     ├── Sprint 3  (Repos)       [depends on 2]
  │     │     ├── Sprint 4  (API+Auth) [depends on 3]
  │     │     │     └── Sprint 5  (Challenge Data) [depends on 2]
  │     │     └── Sprint 5  (Challenge Data) [depends on 2]
  │     └── Sprint 6  (Challenge Engine) [depends on 5, 3]
  │           └── Sprint 7  (Challenge API) [depends on 6, 4]
  ├── Sprint 5  (Challenge Data) → Sprint 8  (Content Filter) [depends on 5, 3]
  │     └── Sprint 9  (AI Providers) [depends on 5, 8]
  │           └── Sprint 10 (AIService) [depends on 9, 8, 6, 3]
  │                 └── Sprint 11 (Voting Service) [depends on 10, 3]
  │                       ├── Sprint 12 (Scoring Service) [depends on 11, 6, 3]
  │                       │     └── Sprint 13 (Session Service) [depends on 12, 11, 10]
  │                       │           └── Sprint 14 (WebSocket) [depends on 13, 11, 12, 4]
  │                       └── Sprint 14 (WebSocket)
  ├── Sprint 15 (Frontend Scaff) [depends on 1]
  │     ├── Sprint 16 (API Client) [depends on 15, 4]
  │     │     └── Sprint 17 (Auth Context) [depends on 16, 4, 15]
  │     ├── Sprint 18 (ChallengeView) [depends on 15, 16, 8]
  │     │     └── Sprint 19 (Voting Screen) [depends on 18, 17, 14, 16]
  │     │           └── Sprint 20 (Reveal) [depends on 19, 14]
  │     │                 └── Sprint 21 (Session Flow) [depends on 20, 19, 18, 14]
  │     └── Sprint 22 (Leaderboard) [depends on 15, 16, 12]
  └── Sprint 23 (Settings) [depends on 15, 17]
      ├── Sprint 24 (E2E Test) [depends on all]
      ├── Sprint 25 (Share) [depends on 13, 21]
      ├── Sprint 26 (Challenge Load) [depends on 5, 7]
      └── Sprint 27 (Deploy) [depends on all]
```

## Changelog

| Date | Change |
|------|--------|
| 2026-10-08 | Sprint 18 complete: ChallengeView (prompt, hard/bonus constraint list, difficulty + time-limit badges), Timer (deadline-based countdown, bar + seconds, yellow under 10s, red at 5s, "Time!" marker), EntryInput (single/multi-line, live word/char counts against the challenge's limits, hard-violation error + disabled submit, soft-violation note), plus StreakBadge, RatingDisplay (gain/loss change indicator), `useTimer` (urgency states, expiry callback, stop/reset), and `useChallenges` (daily lookup, definition load, server validation). The Challenge page wires them together through the stateless practice path. A client-side `lib/constraints.ts` mirrors the backend ConstraintEngine for live feedback (server stays authoritative; heuristic constraints stay backend-only). 78 frontend tests green (32 new). Vitest config gained `fileParallelism: false` — test files share the module-level api client. Live-verified `useChallenges` against the real backend. |
| 2026-10-08 | Sprint 17 complete: AuthContext + useAuth — auto guest-login on first visit (resuming the persisted guest_id), stored-token validation via `/auth/me` on load, login/register/loginAsGuest actions, logout that survives reloads (explicit `loggedOut` marker so auto-guest doesn't undo it), and a `RequireAuth` route guard (session/challenge/leaderboard/profile/settings gated; `/` and `/auth` public). Auth page wired to the context (sign-in / register / guest with error display via `toApiError`), nav shows the player name + log out. 46 frontend tests green (13 new). Live-verified against the real backend: fresh visit → guest + protected route renders; remount with the token → `/auth/me` restores. Also added a `path="*"` NotFound route — React Router v6 drops the entire layout branch for unmatched URLs (blank page otherwise). |
| 2026-10-08 | Sprint 16 complete: typed API client — 7 resource modules (`authApi`, `challengesApi`, `sessionApi`, `votingApi`, `leaderboardApi`, `profileApi`, `shareApi`) over the Sprint 15 Axios instance, with `toApiError` normalizing 401/404/400-violation/500 payloads into `{status, message, details}`. Shared TS types mirror the backend pydantic schemas exactly (challenge definitions keep the file's camelCase; REST responses are snake_case; the WebSocket `SESSION_STARTED` payload is camelCase). 33 frontend tests green (21 new: per-module URL/payload/return assertions via axios-mock-adapter, JWT request interceptor, 401 token eviction + other-status retention, error mapping). Verified **live against the real backend**: guest → daily → definition → validate → start → state → entry → vote → both leaderboards → next, all shape-checked. `tsc`/`eslint`/`prettier` clean; build OK. |
| 2026-10-08 | Sprint 15 complete: frontend scaffolding — React Router v6 with all 7 routes (Home, Session, Challenge, Leaderboard, Profile, Auth, Settings) in a shared nav layout, Tailwind CSS + shadcn/ui primitives (Button, Card, Input, Badge with the HSL token theme), Axios client with base URL + JWT interceptor, `@/` path alias, ESLint + Prettier + Vitest/jsdom toolchain. 12 frontend tests green (per-route rendering, nav navigation, active-route state, home CTA, auth form); `tsc --noEmit` + `eslint` + `prettier --check` clean; production build OK (202KB JS / 11KB CSS); dev server verified live (SPA shell + fallback + transforms + Tailwind pipeline). Note: `.eslintrc.cjs` (not `.js`) — the package is `"type": "module"`, so ESLint 8 cannot read a `.js` config. |
| 2026-10-08 | Sprint 14 complete: WebSocket layer — `WebSocketManager` (per-session pub/sub topic, dead-socket cleanup), event handlers for `SUBMIT_ENTRY`/`VOTE`/`PING` driving SessionService, `/ws/session/{session_id}?token=...` registered in main.py. Auth happens before accept (invalid token or foreign session → 403 at the handshake); on connect the client gets `SESSION_STARTED` + `ROUND_START` for the current round (rejoin-safe — state lives in SQLite); `SESSION_END` is replayed when reconnecting to a finished session. 228 tests green (15 new), ruff/mypy clean, 100% coverage on the websocket package. **Fix: `websockets>=12.0` added to pyproject/requirements** — it was in Master §8 from the start but was never installed, so uvicorn could not upgrade WebSocket requests at all ("No supported WebSocket library detected"); the live verification proved the real socket path (403 for bad tokens, 101 + full 3-round game for good ones). |
| 2026-10-08 | Sprint 13 complete: SessionService — round state machine (`writing`→`reveal_ai`→`voting`→`scored`, invalid transitions rejected), full round lifecycle (assign → human+AI entries → anonymized A/B → vote → reveal → score → rating/streaks), 3-round session orchestration with completion + summary (total, accuracy, per-round breakdown). The Sprint 12 scoring composition runs here via `SessionService.vote`. REST game loop is now playable: `/session/start` (creates round 1) → `/session/{id}/rounds/{round_id}/entry` → `/voting/vote` (reveal + score) → `/session/{id}/next` → `/session/{id}/summary`. Ownership enforced on every session-scoped call. 213 tests green (26 new), ruff/mypy clean, 100% coverage on new service/router, verified end-to-end on the real Ollama chain (3 rounds, streak bonuses accumulating, rating 1000→1022.3). |
| 2026-10-08 | Sprint 12 complete: ScoringService (§12.5 round score with component breakdown, ELO Detection Rating per GDD §6.2 with K=32/16, floor 100, humanity recomputation from votes with the letter derived from `reveal_data`, correct-guess + daily streaks), LeaderboardService (daily ranked by score with accuracy from the base component, all-time ranked by rating with accuracy from `reveal_data.vote_correct`, idempotent daily snapshots), `GET /leaderboard/daily|all-time` (public reads per §2.4). The Sprint 6-flagged GDD-vs-Master scoring tension is resolved: the GDD's "wrong guess: 0" row is the guess component (§12.5's `guess_bonus`), not the whole round — time/streak bonuses still apply; documented in §5.4. 187 tests green (16 new), ruff/mypy clean, 92-100% coverage on new files, manual verification passed (115/15 scores, 1000→1016→999.3 rating, board + snapshot + HTTP). |
| 2026-10-08 | Sprint 11 complete: VotingService — seeded-per-round A/B assignment (single source shared by presentation and reveal, so they can never disagree), vote recording, reveal with attribution + deterministic explanation, and HumanityScoring (share of voters who guessed each entry was human, 0-100) persisted to `humanity_scores` + mirrored into `rounds.reveal_data`. `POST /voting/vote` records the vote and returns the reveal in one response; 404/400/409 error mapping. 171 tests green (21 new), ruff/mypy clean, 99-100% coverage on new files, manual verification passed (stability, spread, attribution, HTTP double-vote 409). |
| 2026-10-08 | Sprint 10 complete: AIService (prompt build from v1.0 template + per-challenge guidance, chain walk with provider-failure and dirty-response fall-through, `retry_on_injection`, sanitization, audit recording of raw + sanitized + provider/model) + `POST /voting/submit-entry` (validates the human entry, blocks hard violations, triggers generation, records the audit row). Verified live on the real chain: `qwen3.5:9b` produced "Dragon's fire, fresh baked." through HTTP. New `OLLAMA_TIMEOUT` config (default 120s) so GPU contention with other local workloads degrades to the StubProvider instead of hanging. 149 tests green (26 new), ruff/mypy clean, 100% coverage on new files. |
| 2026-10-08 | Sprint 9 complete: AI provider ABC + OpenAI/Anthropic/Stub providers per spec, **plus OllamaProvider** (owner-approved addition — local LLM option per Scope Constraint 7; no key, no external call). Chain: OpenAI → Anthropic → Ollama → Stub, built/selected by `build_provider_chain`/`select_provider` in `providers/__init__.py`; `STUB_PROVIDER_ONLY` still collapses to Stub for E2E. ABC gained optional keyword-only `challenge_id` (StubProvider needs it for pool selection). Ollama config: `OLLAMA_ENABLED`/`OLLAMA_BASE_URL`/`OLLAMA_MODEL` (default `qwen3.5:9b`). Local bake-off (6 models, real challenge prompts scored by ConstraintEngine + ContentFilter) selected the default and established that qwen3-family models **must** be sent `think:false` — they otherwise burn the whole token budget on hidden reasoning and return empty. 123 tests green (19 new), ruff/mypy clean, 83–100% coverage on new files, real Ollama round-trip verified. |
| 2026-10-08 | Sprint 8 complete: ContentFilter (meta-mention stripping, injection detection, system-prompt leakage sentence removal, 500-char truncation with word-boundary cut, `validate_response` gate) + PromptAuditService (version-keyed templates from `app/data/ai_prompts/`, active version from `AI_PROMPT_VERSION`, `record_usage` storing raw + sanitized response in `prompt_audit`); internal services only, no endpoints; 104 tests green (25 new), ruff/mypy clean, 100% coverage on new files. |
| 2026-10-01 | Sprint 7 complete: challenge + session REST endpoints (daily with auto session, definition, validate, session start/state/summary with ownership checks); startup now syncs the JSON library into the `challenges` table (idempotent — core of Sprint 26 pulled forward so `challenge_daily`'s FK is satisfiable); 79 tests green, ruff/mypy clean. Worklog/changelog dates corrected 2026-09-28 → 2026-10-01 (session's actual date). |
| 2026-10-01 | Sprint 6 complete: ChallengeService (in-memory JSON library, fixed-seed permutation daily rotation — deterministic and full-cycle, persisted via challenge_daily), ConstraintEngine (8 types, hard/soft split, documented heuristics for rhyme/adjectives), ScoringEngine (§12.5 formula), InputValidator, ChallengeDefinition schemas (camelCase aliases → snake_case); 70 tests green, ruff/mypy clean. |
| 2026-10-01 | Sprint 5 complete: 25 challenge JSONs (doc 05 catalog), 25 stub-entry pools of 10 human-quality entries each, prompt template `v1.0.json`; schema/counts validated by `tests/test_challenge_library.py` (executable acceptance criteria). Schema gained required `aiPromptGuidance` (per-challenge AI style from doc 05); challenge IDs follow doc 05 (sprint's example `challenge_caption_02.json` was stale — #02 is "Impossible Product"). |
| 2026-10-01 | Sprint 4 complete: JWT auth (PyJWT, HS256) with guest/login/register + protected `/auth/me`, stdlib PBKDF2 password hashing (passlib avoided — unmaintained, not in §8), in-process state store, custom exception handling; `users.password_hash` added via migration 002 (sprint said "no DB changes" but password login requires it); 25 tests green, ruff/mypy clean. |
| 2026-10-01 | Sprint 3 complete: six repositories (users, challenges, sessions, voting, scoring, prompt audit) over the SQLite layer with graceful not-found handling, injectable-RNG A/B anonymization, and daily-score aggregation; TDD 18 green, ruff/mypy clean. |
| 2026-10-01 | Sprint 2 complete: 13-table SQLModel schema + 18 indexes on SQLite (WAL, foreign keys per connection), Alembic `001` migration, DB init wired into the FastAPI lifespan; TDD green, ruff/mypy clean. Sprint text corrected from 14 to 13 tables (13 game tables + the `alembic_version` system table). |
| 2026-10-01 | Sprint 1 complete: FastAPI + Vite scaffolding, TDD health check, pydantic settings, `scripts/dev.py` one-command local dev; ruff/mypy/tsc clean; no Docker. |
| 2026-10-01 | Delivery model revised to a local-first web dashboard: Docker Compose removed (Sprints 1, 27), SQLite replaces PostgreSQL (Sprint 2), in-process state replaces Redis (Sprints 4, 14). Sprint order, game design, and AI fairness rules unchanged. Hosted deployment (PostgreSQL/Redis/Nginx) deferred to post-MVP. |

---

*This is Document 3 of 5. For architecture overview, see `docs/01_Master_Architecture.md`. For technical reference, see `docs/02_Implementation_Guide.md`. For challenge definitions, see `docs/05_Micro_Challenge_Library.md`.*