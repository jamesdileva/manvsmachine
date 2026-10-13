# Man vs. Machine — Master Architecture

> **Version:** 1.27
> **Status:** Final — MVP complete (Sprints 0–27 shipped)
> **Audience:** Developers, AI coding agents, project maintainers
> **Related:** See `docs/04_Game_Design_Document.md` for gameplay experience and `docs/02_Implementation_Guide.md` for technical reference.

This is the single source of truth for what Man vs. Machine is and how it is structured. Every future document — the Implementation Guide, the Sprint Plan, the Micro Challenge Library — derives from and references this document. Read this first.

---

## Table of Contents

1.  Vision
    - 1.1 The Man vs. Machine Pipeline
2.  Design Philosophy
3.  Project Rules
    - 3.1 Scope Constraint (Critical)
4.  Goals
5.  Non-Goals
6.  MVP Definition
7.  High-Level Architecture
    - 7.1 Layered Architecture
8.  Technology Stack
9.  Folder Structure
10. Backend Architecture
    - 10.1 Layer Architecture
    - 10.2 Internal Components
    - 10.3 Module Breakdown
11. Frontend Architecture
    - 11.1 Layer Architecture
    - 11.2 Internal Components
12. Challenge Engine (Micro Challenge Framework)
    - 12.1 Challenge Object Model
    - 12.2 Constraint Engine
    - 12.3 Time Limit System
    - 12.4 Input Validators
    - 12.5 Scoring Rules Engine
    - 12.6 Challenge Rotation
13. AI Layer
    - 13.1 Provider Abstraction
    - 13.2 Prompt Pipeline
    - 13.3 Prompt Security
    - 13.4 Prompt Versioning
    - 13.5 Humanity Scoring
14. Voting System (Bluff Mode)
    - 14.1 Anonymous Presentation
    - 14.2 Voting Flow
    - 14.3 Reveal System
15. Database Architecture
    - 15.1 Schema Overview
    - 15.2 Key Tables
16. Real-time Communication
    - 16.1 WebSocket Events
17. Competitive Systems (Future)
18. Social Features (Future)
19. Future Expansion
20. Agent Development Guidelines
21. Testing Strategy
22. Changelog

Appendix A: API Reference (Summary)
Appendix B: Future Roadmap

---

## 1. Vision

> **North Star:** Man vs. Machine is a micro-challenge game where humans and AI compete side-by-side, and the player's task is to identify which answer the AI wrote — turning the question "is AI better than us?" into a 30-second game of social deduction.

### 1.1 The Man vs. Machine Pipeline

```
Challenge (from Micro Challenge Library)
    │
    │  Same prompt + constraints to both
    ▼
┌─────────────────┐    ┌─────────────────┐
│   Human Player  │    │      AI         │
│                 │    │  (provider API) │
│  Writes entry   │    │  Writes entry   │
│  (15-60s timer) │    │  (no time limit)│
└─────────────────┘    └─────────────────┘
    │                         │
    │  Both entries anonymized│
    ▼                         ▼
┌───────────────────────────────────────┐
│           Voting Screen               │
│   Entry A: "..."                      │
│   Entry B: "..."                      │
│   Which was written by AI? [A] [B]    │
└───────────────────────────────────────┘
    │
    │  Vote submitted
    ▼
┌───────────────────────────────────────┐
│           Reveal + Score              │
│   A = Human ◄── Player's entry       │
│   B = AI   ◄── AI's entry            │
│   ✓ Correct! +100 pts                │
│   Humanity Score updated             │
└───────────────────────────────────────┘
    │
    ▼
Next Round (3 rounds per session) → Session Summary → Leaderboard
```

Every 15–60 seconds, the player goes through this cycle. The tension is not "can I write better than the AI?" but **"can I tell which entry the AI wrote?"** — and over time, the system tracks the fascinating meta-question: *do players systematically misattribute high-quality or low-effort answers?*

---

## 2. Design Philosophy

| Principle | Description |
|-----------|-------------|
| **Micro-first** | Every challenge is designed for 15–60 seconds of play. No open-ended tasks that take minutes. Constraints and tight time limits create the addictive loop. |
| **Social deduction over competition** | The win condition is guessing correctly, not out-writing the AI. This keeps the game fair regardless of the player's skill level. |
| **Constraint-based design** | Challenges are data-driven: prompt + constraints + time limit + input type + voting criteria + scoring rules. The engine interprets these; no hard-coded challenge logic. |
| **AI as collaborative entry** | The AI is not an opponent to defeat. It is a co-author in the same challenge. The game tension comes from detection, not out-performance. |
| **Fast feedback** | Immediate reveal, immediate scoring, immediate leaderboard update. No waiting. |
| **Web-first, local-first** | The game runs in the browser against a local server (localhost). No Docker, no installs, no Steam. A hosted deployment is a post-MVP option. |
| **Provider-agnostic AI** | The AI layer supports multiple providers (OpenAI, Anthropic, local Ollama). The game logic never depends on a specific provider's output format or quality. |
| **Transparent humanity** | Both human and AI entries are scored for "humanity" — how human-like they appear. This is surfaced to the player as a meta-metric. |

---

## 3. Project Rules

These are the "constitution" of Man vs. Machine. They must be upheld in every decision.

1.  **Challenges are data, not code.** All challenge definitions (prompts, constraints, time limits, scoring rules) live in the Micro Challenge Library as JSON/YAML. Adding a new challenge requires no code change.
2.  **The AI gets the same prompt as the human.** No special instructions that the human doesn't see. The AI prompt is a deterministic transformation of the challenge definition.
3.  **Time asymmetry is the game mechanic, not a bug.** The AI has unlimited time; the human has 15–60 seconds. This is intentional and core to the design.
4.  **No raw prompt leakage.** The AI system prompt must never mention it is an AI, nor reference the game's rules, nor acknowledge the human competitor.
5.  **Humanity is measurable and transparent.** Every entry (human or AI) receives a humanity score. This feeds into challenge balance and player ratings.
6.  **Every feature must be testable independently.** No feature is deployed without unit or integration tests.
7.  **Business logic belongs in backend services.** The frontend is a thin presentation layer. All game logic, scoring, AI orchestration lives in Python services.
8.  **One responsibility per module.** Each service, repository, and component does exactly one thing.
9.  **Real-time voting is stateful.** The voting/reveal flow is managed via WebSocket sessions. Clients cannot forge votes or skip states.
10. **Provider fallback is mandatory.** If the primary AI provider fails, the system falls back to a secondary provider. If all providers fail, the round is gracefully degraded (AI entry is generated from a template pool).

### 3.1 Scope Constraint (Critical)

1.  **The game is NOT about beating the AI.** The core mode is social deduction: guessing which entry is AI. This is the fundamental experience — every feature, every sprint, every line of code must serve this.
2.  **No open-ended long-form challenges in MVP.** All MVP challenges are Quick Text (15–60 seconds). Visual, Build, Explain, Strategy modes are post-MVP.
3.  **No real-time multiplayer in MVP.** All MVP rounds are human-vs-AI. True multiplayer (2+ humans + voting) is post-MVP.
4.  **No user-generated content in MVP.** The Micro Challenge Library is curated, not community-submitted.
5.  **No monetization in MVP.** The MVP is completely free. Monetization strategy is documented but not implemented.
6.  **Web-first, no desktop app.** The game runs in the browser against a local backend server. No Tauri/Electron/installed application. No Docker required for development or play.
7.  **AI providers are external services.** The system uses APIs (OpenAI, Anthropic, etc.). Local LLM support (Ollama) is a configuration option, not the primary path.
8.  **The AI prompt must be auditable.** Every AI prompt used in a round is stored and versioned. System prompt modifications require a changelog entry.
9.  **Prompt injection protection.** AI responses are validated/sanitized before presentation to players. No unfiltered LLM output reaches the UI.

---

## 4. Goals

### Must-Have (MVP)

- Web application (React + TypeScript frontend, FastAPI backend)
- Micro Challenge Framework: challenge definitions as data, constraint engine, time limit system, input validators
- Bluff mode: human writes entry → AI generates entry → anonymous voting → reveal → scoring
- 3 rounds per session, with daily challenge
- AI provider abstraction layer supporting at least OpenAI (fallback to a stub/local model)
- Humanity scoring per entry (0–100), aggregated across rounds
- Detection Rating (ELO-style) for each player
- Daily leaderboard (top accuracy for today's challenge)
- User accounts with guest mode (no signup required, persistent via localStorage + server-side guest ID)
- Streak tracking (daily challenge streak)
- Prompt versioning system (audit trail for AI prompts)
- Prompt injection protection (response sanitization)
- WebSocket-based real-time voting flow
- Shareable result cards (text summary + static image)

### Should-Have (Post-MVP)

- Weekly challenges (themed 5-round sessions)
- Additional interaction types: Visual, Build, Explain, Strategy
- True multiplayer Bluff mode (2+ humans + 1 AI, voting)
- Community challenge submission + review
- Battle Pass (seasonal progression)
- Local LLM support (Ollama integration as an option)
- Practice mode (unlimited random challenges)

### Could-Have (Future)

- Tournament brackets (weekly elimination)
- Creator mode (player-designed challenges)
- Mobile app (PWA or native)
- Corporate training variant
- AI benchmark platform

---

## 5. Non-Goals

- **Not a hosted multi-user service in the MVP.** The game runs locally: the backend is a local FastAPI process with SQLite, and no Docker/Redis/Postgres are required. A hosted deployment (PostgreSQL, Redis, global daily challenge, shared leaderboards) is a post-MVP expansion (Appendix B).
- **Not a general AI chat interface.** The AI is only used to generate challenge entries. No free-form chat.
- **Not a content generation platform.** The game does not let users create challenges in the MVP.
- **Not a social network.** There are no user profiles beyond a display name and stats. No friend lists, no messaging.
- **Not a real-time multiplayer game in MVP.** All rounds are human-vs-AI. The "voting" is guessing which entry is AI.
- **No paywall.** The MVP is fully free. Monetization is deferred.
- **No native mobile app in MVP.** The web app must be mobile-responsive, but no native iOS/Android build.

---

## 6. MVP Definition

The MVP is the minimal set of features that demonstrates the core value proposition: **a 30-second-per-round micro-challenge game where humans and AI write side-by-side and the player guesses which is which.**

### In Scope

| Component | Status |
|-----------|--------|
| Web frontend (React + TS) | Core |
| Backend API (FastAPI) | Core |
| WebSocket real-time voting | Core |
| Micro Challenge Framework (challenge definitions, constraints, time limits) | Core |
| 20+ challenge templates (Quick Text: Slogans, Product Names, Captions, Comebacks) | Core |
| AI provider abstraction (OpenAI primary, stub fallback) | Core |
| Bluff mode game loop (human write → AI write → vote → reveal → score) | Core |
| 3-round session with daily challenge | Core |
| Humanity scoring per entry | Core |
| Player Detection Rating (ELO-style) | Core |
| Daily leaderboard | Core |
| Guest mode + optional account creation | Core |
| Streak tracking | Core |
| Prompt versioning + audit trail | Core |
| Prompt injection protection | Core |
| Shareable result cards | Core |

### Out of Scope (MVP)

- Weekly challenges
- Multiplayer mode (2+ humans)
- Visual, Build, Explain, Strategy challenge types
- Community challenge submission
- Battle Pass / cosmetics shop
- Local LLM support
- Native mobile apps
- Tournament mode
- Creator mode

### Success Criteria

The MVP is complete when a user can:

1.  Open the web app in a browser (no install required)
2.  Play as a guest (no signup)
3.  See today's daily challenge (e.g., "Write a slogan for a dragon-owned bakery")
4.  Write their answer in 15 seconds while a visible timer counts down
5.  See both their entry and the AI's entry, anonymized as "Entry A" and "Entry B"
6.  Vote which entry is the AI's
7.  See the reveal: "A = Human, B = AI" with a brief explanation
8.  See their updated Detection Rating and humanity score
9.  See the daily leaderboard
10. Share their result ("3/3 — detected the AI!")
11. Return the next day for a new challenge

---

## 7. High-Level Architecture

### 7.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                                      │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │           Frontend (React + TypeScript + Vite)             │            │
│  │  Home • Session • Challenge • Voting • Results • Profile  │            │
│  └───────────────────────────────────────┬─────────────────────┘            │
│                                          │ HTTP/REST + WebSocket           │
│                                          ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                  Backend (Python / FastAPI)                     │        │
│  │                                                                 │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │        │
│  │  │ Challenge    │  │ AI Service   │  │ Voting Service   │   │        │
│  │  │ Engine       │  │              │  │                  │   │        │
│  │  │              │  │ Provider     │  │ Anonymous        │   │        │
│  │  │ Constraints  │  │ Abstraction  │  │ Voting           │   │        │
│  │  │ Time Limits  │  │ Prompt       │  │ Reveal           │   │        │
│  │  │ Rotations    │  │ Pipeline     │  │                  │   │        │
│  │  └──────────────┘  │ Prompt       │  └──────────────────┘   │        │
│  │        │           │ Security     │           │             │        │
│  │        ▼           │ Humanity     │           ▼             │        │
│  │  ┌──────────────────────────────────────┐                  │        │
│  │  │        Scoring Service              │                  │        │
│  │  │  Detection Rating (ELO)              │                  │        │
│  │  │  Humanity Score (0–100)              │                  │        │
│  │  │  Streaks & Achievements              │                  │        │
│  │  └──────────────────────────────────────┘                  │        │
│  │        │                                                    │        │
│  │        ▼                                                    │        │
│  │  ┌──────────────────────────────────────┐                  │        │
│  │  │          Session Service            │                  │        │
│  │  │  Round state machine                │                  │        │
│  │  │  Multi-round session orchestration  │                  │        │
│  │  │  WebSocket connection management    │                  │        │
│  │  └──────────────────────────────────────┘                  │        │
│  │        │                                                    │        │
│  │        ▼                                                    │        │
│  │  ┌──────────────────────────────────────┐                  │        │
│  │  │            SQLite Database           │                  │        │
│  │  │  users • challenges • rounds          │                  │        │
│  │  │  ai_entries • scores • prompts        │                  │        │
│  │  └──────────────────────────────────────┘                  │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│                                          │                                 │
│                                          ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │          External AI Providers (OpenAI, Anthropic, etc.)        │        │
│  └─────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Summary

1.  **Challenge Assignment**: Session Service selects a challenge → Challenge Engine applies constraints & time limit → prompt pushed to both frontend and AI Service
2.  **Human Entry**: Player writes entry in the browser → submitted via WebSocket → stored in `rounds` table
3.  **AI Entry**: AI Service calls provider API with constructed prompt → response sanitized → stored in `ai_entries` table
4.  **Voting**: Both entries anonymized (A/B) → pushed to frontend → player votes via WebSocket → vote stored
5.  **Scoring**: Scoring Service calculates humanity scores, updates Detection Rating → results pushed to frontend
6.  **Progression**: Leaderboard updated, streak evaluated, result card generated

---

## 8. Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.110+ | REST API framework |
| aiosqlite | 0.20+ | SQLite async driver |
| SQLModel | 0.0.14+ | ORM models (sync layer for batch ops) |
| SQLAlchemy | 2.0+ | Core async ORM for complex queries |
| pydantic | 2.5+ | Data validation and serialization |
| PyJWT | 2.8+ | JWT issuing/validation (auth) |
| websockets | 12.0+ | WebSocket server for real-time voting |
| pytest | 8.0+ | Backend testing |
| uvicorn | 0.29+ | ASGI server |
| httpx | 0.26+ | Async HTTP client for AI provider calls |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18+ | UI library |
| TypeScript | 5.3+ | Type safety |
| Vite | 5.0+ | Build tool |
| React Router | 6.14+ | Client-side routing |
| Axios | 1.6+ | HTTP client |
| shadcn/ui | 0.6+ | Component library |
| Tailwind CSS | 3.4+ | Styling |
| Socket.IO Client | 4.7+ | WebSocket client — *realized as the browser's native WebSocket; the backend speaks raw JSON frames, so no Socket.IO dependency was installed* |
| Chart.js | 4.4+ | Leaderboard charts — *installed in Sprint 22 for the profile humanity trend* |
| Vitest | 1.2+ | Frontend testing |
| html2canvas | 1.4+ | Result card image generation (client-side) — *not installed; the MVP card is rasterised server-side with stdlib `zlib`/`struct` (Sprint 25)* |

### Build / Packaging

| Technology | Version | Purpose |
|------------|---------|---------|
| PyInstaller | 6.11+ | Freezing the app into a double-click desktop bundle |

**PyInstaller is an owner-approved addition** (see §22 changelog v1.24). It is a
build-time-only tool, not a runtime dependency of the game: the app itself still
runs on plain FastAPI + SQLite + the Vite build output, exactly as it does in
dev and release mode. The spec lives at `packaging/manvsmachine.spec`, the entry
point at `packaging/launcher.py`, and `scripts/build_executable.py` orchestrates
the build.

### Infrastructure

| Technology | Purpose |
|------------|---------|
| SQLite (WAL mode) | Primary database (local file) |
| In-process state store | Ephemeral round/WebSocket state (replaces Redis) |
| GitHub Actions | CI/CD |
| (Future, hosted) PostgreSQL + Redis + Nginx | Post-MVP hosted deployment |

### AI Providers

| Provider | Primary | Fallback |
|----------|---------|----------|
| OpenAI (GPT-4o, GPT-4o-mini) | Default | Yes |
| Anthropic (Claude 3 Haiku/Sonnet) | Secondary | Yes |
| Ollama (local Llama 3, etc.) | Optional config | Yes (stub entries) |

### Why This Stack

- **FastAPI**: Modern, type-safe, async-native, excellent auto-generated OpenAPI docs. Perfect for the mixed REST+WebSocket workload.
- **SQLite**: Zero-configuration local database; JSON columns hold challenge definitions and constraint lists; easily handles single-player write volumes; backup is copying one file. Schema and queries stay SQLAlchemy-portable so a future hosted deployment can move to PostgreSQL without service-layer changes.
- **React + TypeScript**: Industry standard for web apps. TypeScript catches errors early in the voting/reveal UI which has complex state transitions.
- **WebSockets**: Required for the real-time voting flow — the player must not be able to see the AI's response before voting, and the reveal must be synchronized.
- **In-process state store**: The MVP is single-player (one client per session), so ephemeral round state and WebSocket broadcasts live in the backend process. Redis becomes necessary only for a hosted multi-user deployment.

---

## 9. Folder Structure

```
manVSmachine/
├── docs/
│   ├── 01_Master_Architecture.md     ← This file
│   ├── 02_Implementation_Guide.md
│   ├── 03_Sprint_Plan.md
│   ├── 04_Game_Design_Document.md
│   ├── 05_Micro_Challenge_Library.md
│   └── resources/                    # Diagrams, assets
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry point, ASGI + WebSocket setup
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── challenges.py     # Challenge CRUD + daily challenge endpoint
│   │   │   │   ├── session.py        # Session start, round state
│   │   │   │   ├── voting.py         # Vote submission, reveal trigger
│   │   │   │   ├── scoring.py        # Rating updates, humanity scores
│   │   │   │   ├── leaderboard.py    # Daily/weekly/all-time leaderboards
│   │   │   │   ├── user.py           # Auth, profile, settings
│   │   │   │   ├── prompt_audit.py   # Prompt versioning, audit trail
│   │   │   │   └── share.py          # Result card generation
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic settings
│   │   │   ├── logging.py            # Logger setup
│   │   │   ├── security.py           # JWT, password hashing
│   │   │   ├── exceptions.py         # Custom exceptions
│   │   │   └── state.py              # In-process ephemeral state (replaces Redis)
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py         # Async SQLite (aiosqlite) + sync for batch
│   │   │   ├── models.py             # SQLModel/SQLAlchemy table definitions
│   │   │   └── migration.py          # Alembic migrations
│   │   ├── schemas/                  # Pydantic schemas
│   │   │   ├── challenge.py
│   │   │   ├── session.py
│   │   │   ├── voting.py
│   │   │   ├── scoring.py
│   │   │   ├── user.py
│   │   │   └── share.py
│   │   ├── repositories/
│   │   │   ├── base.py
│   │   │   ├── challenge.py
│   │   │   ├── session.py
│   │   │   ├── voting.py
│   │   │   ├── scoring.py
│   │   │   ├── user.py
│   │   │   └── prompt_audit.py
│   │   ├── services/
│   │   │   ├── challenge_service.py    # Challenge Engine: constraints, time limits, rotation
│   │   │   ├── ai_service.py           # AI provider abstraction, prompt pipeline
│   │   │   ├── voting_service.py       # Anonymous voting, reveal orchestration
│   │   │   ├── scoring_service.py      # ELO, humanity scoring, streaks
│   │   │   ├── session_service.py      # Round state machine, session orchestration
│   │   │   ├── leaderboard_service.py  # Leaderboard computation
│   │   │   ├── prompt_audit_service.py # Prompt versioning, audit trail
│   │   │   ├── content_filter.py       # Prompt injection protection / sanitization
│   │   │   └── share_service.py        # Result card generation
│   │   ├── websocket/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py              # WebSocket connection manager
│   │   │   └── handlers.py             # WebSocket event handlers (vote, reveal, etc.)
│   │   ├── data/
│   │   │   ├── challenge_library/      # Micro Challenge Library (JSON/YAML files)
│   │   │   ├── ai_prompts/             # Prompt templates by version
│   │   │   └── recommendation_templates/ # AI humanity prompt variants
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── test_repositories.py
│   │       ├── test_services.py
│   │       ├── test_ai_service.py
│   │       ├── test_challenge_engine.py
│   │       ├── test_voting.py
│   │       ├── test_scoring.py
│   │       ├── test_websocket.py
│   │       └── test_e2e.py
│   ├── alembic/                        # Database migrations
│   │   └── versions/
│   ├── tests/                          # Integration tests
│   ├── scripts/
│   │   ├── run.sh
│   │   └── migrate.sh
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── app.tsx
│   │   ├── api/
│   │   │   ├── client.ts               # Axios instance
│   │   │   ├── challenges.ts
│   │   │   ├── session.ts
│   │   │   ├── voting.ts
│   │   │   ├── scoring.ts
│   │   │   ├── leaderboard.ts
│   │   │   ├── user.ts
│   │   │   └── share.ts
│   │   ├── websocket/
│   │   │   ├── client.ts               # Socket.IO/WebSocket client wrapper
│   │   │   ├── events.ts              # Typed events (ROUND_START, AI_RESPONSE, REVEAL, etc.)
│   │   │   └── hooks.ts               # useWebSocket, useVoting, useReveal
│   │   ├── components/
│   │   │   ├── ChallengeView.tsx       # Prompt + constraints display
│   │   │   ├── Timer.tsx               # Countdown timer
│   │   │   ├── EntryInput.tsx           # Human entry input (text area)
│   │   │   ├── VotingScreen.tsx         # A/B entries + vote buttons
│   │   │   ├── RevealScreen.tsx         # Reveal + score + humanity
│   │   │   ├── Leaderboard.tsx          # Daily rankings
│   │   │   ├── SessionSummary.tsx       # End-of-session stats
│   │   │   ├── ResultCard.tsx           # Shareable result
│   │   │   ├── StreakBadge.tsx          # Daily streak indicator
│   │   │   └── RatingDisplay.tsx        # Detection Rating
│   │   ├── contexts/
│   │   │   ├── SessionContext.tsx       # Round state, session state
│   │   │   ├── VotingContext.tsx        # Voting phase, entries, vote
│   │   │   ├── ScoringContext.tsx       # Humanity scores, rating updates
│   │   │   └── AuthContext.tsx          # Guest/user auth state
│   │   ├── hooks/
│   │   │   ├── useSession.ts
│   │   │   ├── useVoting.ts
│   │   │   ├── useTimer.ts
│   │   │   ├── useLeaderboard.ts
│   │   │   └── useAuth.ts
│   │   ├── pages/
│   │   │   ├── Home.tsx                 # Daily challenge, streak, leaderboard preview
│   │   │   ├── Session.tsx              # Full session flow (3 rounds)
│   │   │   ├── Challenge.tsx            # Single challenge view
│   │   │   ├── Leaderboard.tsx          # Full leaderboard page
│   │   │   ├── Profile.tsx              # User stats, history
│   │   │   ├── Auth.tsx                 # Login/signup/guest
│   │   │   └── Settings.tsx             # AI provider selection, theme
│   │   ├── routes/
│   │   │   └── index.tsx
│   │   ├── styles/
│   │   └── lib/
│   │       └── utils.ts
│   ├── public/
│   ├── vite.config.ts
│   ├── package.json
│   └── tsconfig.json
├── scripts/
│   ├── dev.py                           # Run backend + frontend + db in dev mode
│   └── build.py                         # Build all artifacts
├── AGENTS.md
├── .python-version
├── pyproject.toml                       # Root pyproject (workspace)
└── README.md
```

---

## 10. Backend Architecture

### 10.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                               │
│  FastAPI Routers (v1: challenges, session, voting, scoring,       │
│  leaderboard, user, share) — thin controllers, delegate to svc   │
├─────────────────────────────────────────────────────────────────┤
│                      Service Layer                              │
│  ChallengeService, AIService, VotingService, ScoringService,     │
│  SessionService, LeaderboardService, PromptAuditService,         │
│  ContentFilter, ShareService                                     │
├─────────────────────────────────────────────────────────────────┤
│                    Repository Layer                             │
│  ChallengeRepository, SessionRepository, VotingRepository,      │
│  ScoringRepository, UserRepository, PromptAuditRepository        │
├─────────────────────────────────────────────────────────────────┤
│                    WebSocket Layer                             │
│  WebSocketManager, WebSocketHandlers                             │
├─────────────────────────────────────────────────────────────────┤
│                      Database Layer                             │
│  SQLite via SQLAlchemy + SQLModel (aiosqlite)                     │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Internal Components

| Component | Module Path | Description |
|-----------|-------------|-------------|
| FastAPI App | `app/main.py` | Application factory, middleware, WebSocket setup, dependency injection |
| API Routers | `app/api/v1/` | REST endpoints grouped by resource |
| Core Config | `app/core/config.py` | Pydantic settings, environment variables, AI provider config |
| State Manager | `app/core/state.py` | In-process ephemeral state for sessions/pubsub (replaces Redis) |
| Database | `app/db/` | Async SQLite connection (SQLAlchemy + aiosqlite), sync for batch ops (SQLModel) |
| Schemas | `app/schemas/` | Pydantic models for API request/response |
| Repositories | `app/repositories/` | CRUD operations, query building |
| Services | `app/services/` | Business logic layer (see 10.3 for breakdown) |
| WebSocket Manager | `app/websocket/manager.py` | Connection lifecycle, pub/sub dispatch |
| WebSocket Handlers | `app/websocket/handlers.py` | Event-specific handlers (SUBMIT_ENTRY, VOTE, etc.) |
| Challenge Library | `app/data/challenge_library/` | JSON challenge definition files |

### 10.3 Module Breakdown

#### ChallengeService (`app/services/challenge_service.py`)

The **Challenge Engine** — the heart of the system.

```python
class ChallengeService:
    def get_daily_challenge(date: date) -> ChallengeDefinition
    def get_challenge(challenge_id: str) -> ChallengeDefinition
    def apply_constraints(entry: str, challenge: ChallengeDefinition) -> ConstraintResult
    def generate_time_limit(challenge: ChallengeDefinition, difficulty: int) -> int
    def rotate_daily_challenge(date: date, pool: list[str]) -> ChallengeDefinition
    def validate_input(entry: str, input_type: str) -> ValidationResult
```

Responsibilities:
- Load challenge definitions from JSON in `app/data/challenge_library/`
- Apply constraints (max_words, max_characters, must_include_theme, etc.)
- Determine time limits based on challenge difficulty
- Validate input types (text_single_line, text_multi_line, sketch, etc.)
- Daily rotation: selects one challenge per day from the pool, applies daily variants

#### AIService (`app/services/ai_service.py`)

The **AI Provider Abstraction** layer.

```python
class AIService:
    def generate_entry(challenge: ChallengeDefinition, model_name: str | None = None) -> str
    def select_provider() -> AIProvider
    def build_prompt(challenge: ChallengeDefinition) -> str
    def sanitize_response(raw: str) -> str  # prompt injection protection
    def record_prompt(prompt: str, response: str, provider: str, prompt_version: str) -> PromptRecord
```

Responsibilities:
- Construct the AI prompt from the challenge definition (deterministic, auditable)
- Route to the selected provider (OpenAI, Anthropic, Ollama stub)
- Apply fallback logic if the primary provider fails
- Sanitize all responses before they reach the voting layer
- Record every prompt + response in the prompt audit trail

**Provider Interface:**

```python
class AIProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> str
    @abstractmethod
    def is_available(self) -> bool
    @abstractmethod
    def get_model_name(self) -> str
```

#### VotingService (`app/services/voting_service.py`)

Manages the **Bluff mode voting flow**.

```python
class VotingService:
    def present_entries(human_entry_id: str, ai_entry_id: str) -> PresentedEntries
    def process_vote(session_id: str, vote: str) -> VoteResult
    def reveal(entries: PresentedEntries, vote: str) -> RevealResult
    def calculate_humanity_score(entry: str, context: VoteContext) -> float
```

Responsibilities:
- Anonymize entries (randomize A/B order)
- Process vote submissions
- Trigger reveal with explanation of why the AI was detectable
- Calculate per-entry humanity scores

#### ScoringService (`app/services/scoring_service.py`)

Handles all scoring and progression.

```python
class ScoringService:
    def calculate_round_score(vote: Vote, human_entry: str, ai_entry: str) -> RoundScore
    def update_detection_rating(player_id: str, correct: bool, ai_rating: float) -> float
    def update_humanity_score(entry_id: str, player_guesses: list[bool]) -> float
    def update_streak(user_id: str, correct: bool) -> StreakUpdate
    def get_leaderboard(date: date, limit: int = 100) -> Leaderboard
```

#### SessionService (`app/services/session_service.py`)

Orchestrates the **round state machine** and 3-round sessions.

```python
class SessionService:
    def start_session(user_id: str, challenge_ids: list[str]) -> Session
    def next_round(session: Session) -> RoundState
    def transition_state(round_id: str, target_state: RoundState) -> bool
    def get_session_summary(session_id: str) -> SessionSummary
```

State machine: `IDLE → WRITING → REVEAL_AI → VOTING → SCORE → RESULT → [next round or end]`

#### ContentFilter (`app/services/content_filter.py`)

Prompt injection protection and content sanitization.

```python
class ContentFilter:
    def sanitize_ai_response(raw: str) -> str
    def check_prompt_injection(text: str) -> InjectionRisk
    def strip_system_prompt_leakage(text: str) -> str
    def validate_no_meta_mentions(text: str) -> bool  # reject "as an AI" etc.
```

#### PromptAuditService (`app/services/prompt_audit_service.py`)

Versioned prompt management and audit trail.

```python
class PromptAuditService:
    def get_prompt_template(version: str) -> str
    def record_usage(prompt_version: str, challenge_id: str, response: str) -> PromptUsage
    def list_versions() -> list[str]
```

---

## 11. Frontend Architecture

### 11.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   State Management                             │
│  React Context: SessionContext, VotingContext,                   │
│  ScoringContext, AuthContext, UIContext                          │
├─────────────────────────────────────────────────────────────────┤
│                   WebSocket Layer                               │
│  WebSocketClient, Typed Events, Hooks                           │
├─────────────────────────────────────────────────────────────────┤
│                   API Client Layer                             │
│  Axios instance + typed hooks                                   │
├─────────────────────────────────────────────────────────────────┤
│                   Component Layer                              │
│  Reusable components (shadcn/ui), page components                │
├─────────────────────────────────────────────────────────────────┤
│                   Routing Layer                                │
│  React Router v6 — declarative client-side routing                │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 Internal Components

| Component | Module Path | Description |
|-----------|-------------|-------------|
| App Root | `src/app.tsx` | Root component, providers, router outlet |
| API Client | `src/api/client.ts` | Axios instance with interceptors |
| API Hooks | `src/api/` | Typed query/mutation hooks per resource |
| WebSocket Client | `src/websocket/client.ts` | Socket.IO or raw WebSocket wrapper |
| WS Events | `src/websocket/events.ts` | Typed event constants + payloads |
| WS Hooks | `src/websocket/hooks.ts` | useWebSocket, useVoting, useReveal |
| Contexts | `src/contexts/` | SessionContext, VotingContext, ScoringContext, etc. |
| Custom Hooks | `src/hooks/` | useSession, useVoting, useTimer, useLeaderboard, useAuth |
| Pages | `src/pages/` | Home, Session, Challenge, Leaderboard, Profile, Auth, Settings |
| Components | `src/components/` | ChallengeView, Timer, EntryInput, VotingScreen, RevealScreen, etc. |
| Utils | `src/lib/utils.ts` | Utility functions |

---

## 12. Challenge Engine (Micro Challenge Framework)

The Challenge Engine is the **heart of the application**. It interprets challenge definitions, applies constraints, manages time limits, and validates inputs. Everything else in the system serves the challenge engine.

### 12.1 Challenge Object Model

```typescript
interface ChallengeDefinition {
  id: string;
  name: string;
  interactionType: "Quick Text";  // Post-MVP: Visual, Build, etc.
  prompt: string;
  constraints: Constraint[];
  timeLimitSeconds: number;
  inputType: "text_single_line" | "text_multi_line";
  votingCriteria: "most_believable";
  difficulty: number;  // 1-5
  scoringRules: ScoringRules;
  aiPromptTemplateId: string;
  aiPromptGuidance: string;  // per-challenge style guidance from the Micro Challenge Library
  replayability: ReplayabilityConfig;
}

interface Constraint {
  type: "max_words" | "max_characters" | "must_rhyme" | "no_adjectives" | 
        "must_include_theme" | "exactly_n_emojis" | "no_letter_e" | "one_sentence_only";
  value: number | string | string[];  // type-dependent
  isHard: boolean;  // hard = blocks submission; soft = tracked only
}

interface ScoringRules {
  baseScore: number;
  timeBonusMultiplier: number;
  streakMultiplier: number;
}

interface ReplayabilityConfig {
  dailyVariants: number;  // number of rotated constraint variants
  constraintPool: string[]; // pool of constraints to rotate through
}
```

### 12.2 Constraint Engine

The Constraint Engine validates entries against challenge constraints at runtime. It returns a structured result:

```python
class ConstraintEngine:
    def validate(self, entry: str, constraints: list[Constraint]) -> ConstraintResult:
        """Returns {valid: bool, violations: list[str], soft_violations: list[str]}"""
```

- **Hard constraints**: If violated, submission is blocked (e.g., max 5 words).
- **Soft constraints**: If violated, the entry is still accepted but penalized in scoring or humanity rating (e.g., "no adjectives" — the entry is accepted but flagged).

### 12.3 Time Limit System

Time limits are derived from the challenge definition but can be adjusted by difficulty:

```python
class TimeLimitSystem:
    def calculate_time_limit(challenge: ChallengeDefinition, 
                              difficulty: int, 
                              player_rating: float | None = None) -> int:
        """Base time from challenge, adjusted by difficulty and adaptive scaling."""
```

**Adaptive difficulty**: If the player is consistently acing challenges (high accuracy), the system may slightly reduce their time limit to increase tension. This is tracked but not enabled by default in MVP.

### 12.4 Input Validators

Each input type has a validator:

| Input Type | Validator Behavior |
|------------|-------------------|
| `text_single_line` | Single-line text, enforces max_characters/max_words constraints |
| `text_multi_line` | Multi-line text with word count, character limit |
| `sketch` (post-MVP) | Canvas drawing data, dimensions, color count |
| `drag_arrangement` (post-MVP) | Array of positions/shapes, adjacency rules |

### 12.5 Scoring Rules Engine

```python
class ScoringEngine:
    def calculate_score(vote_correct: bool, 
                        time_remaining: float, 
                        time_limit: float,
                        streak: int,
                        challenge: ChallengeDefinition) -> int:
        base = challenge.scoringRules.baseScore  # 100
        time_bonus = min(50, base * challenge.scoringRules.timeBonusMultiplier * (time_remaining / time_limit))
        streak_bonus = streak * base * challenge.scoringRules.streakMultiplier
        guess_bonus = base if vote_correct else 0
        return int(guess_bonus + time_bonus + streak_bonus)
```

### 12.6 Challenge Rotation

- **Daily Challenge**: One pre-selected challenge per day. Same for all players globally. Selected via a deterministic hash of the date against the challenge pool.
- **Daily Variants**: Same challenge name, but constraints are rotated (e.g., "max 5 words" vs "max 8 words" vs "must rhyme"). Variants are generated by applying constraints from the `constraintPool` in the replayability config.
- **Session Pool**: Each 3-round session pulls from a pool of 20 challenges (for MVP). The pool rotates daily.

---

## 13. AI Layer

### 13.1 Provider Abstraction

The AI layer uses a provider pattern with fallback:

```
AIService.generate_entry(challenge)
    │
    ├─► build_prompt(challenge)         # constructs prompt from challenge def
    ├─► select_provider()               # primary or fallback
    │     │
    │     ├─► OpenAIProvider.generate(prompt)
    │     │       (calls https://api.openai.com/v1/chat/completions)
    │     │
    │     ├─► AnthropicProvider.generate(prompt)
    │     │       (calls https://api.anthropic.com/v1/messages)
    │     │
    │     ├─► OllamaProvider.generate(prompt)
    │     │       (calls a local Ollama server — optional, Scope Constraint §3.1.7)
    │     │
    │     └─► StubProvider.generate(prompt)
    │             (returns from a pre-written template pool)
    │
    ├─► sanitize_response(raw)          # strip meta-mentions, injection protection
    ├─► record_prompt(...)              # audit trail
    └─► return sanitized entry
```

**OpenAIProvider** is primary. **AnthropicProvider** is fallback #1. **OllamaProvider** is fallback #2 — a local option (no key, no external call) enabled by `OLLAMA_ENABLED`. **StubProvider** is the final fallback (returns pre-written entries from a template pool, ensuring the game never breaks).

### 13.2 Prompt Pipeline

```python
PROMPT_PIPELINE = {
    "v1.0": {
        "system": "You are a creative writing assistant. ...",
        "user_template": "Prompt: {prompt}\nConstraints: {constraints}\n...",
        "instruction": "Do NOT acknowledge you are an AI. Do NOT mention being a large language model. ...",
    }
}
```

Every AI call uses a versioned prompt template. The version is stored alongside every AI entry in the database, ensuring full reproducibility and auditability.

### 13.3 Prompt Security

The ContentFilter enforces:

1.  **No meta-mentions**: Responses containing phrases like "as an AI", "I'm an AI", "as a language model" are rejected and retried.
2.  **Length validation**: Responses must fit within reasonable bounds for the challenge constraints.
3.  **Profanity filter**: Basic profanity detection (configurable, post-MVP moderation).
4.  **Prompt injection detection**: If the AI's response appears to be echoing system prompt content, it is rejected.

### 13.4 Prompt Versioning

- Prompt templates live in `app/data/ai_prompts/` as version-keyed JSON files.
- Each version has a changelog entry.
- The active version is configurable via environment variable (`AI_PROMPT_VERSION`).
- Every AI entry in the database records which prompt version was used.

### 13.5 Humanity Scoring

The humanity score is calculated **retroactively** based on player voting accuracy:

```python
class HumanityScoring:
    def calculate(entry_id: str, votes: list[Vote]) -> float:
        """
        Humanity Score = percentage of players who guessed this entry was human.
        
        If entry is AI and players guessed it was AI → low humanity (AI was detectable)
        If entry is AI and players guessed it was human → high humanity (AI fooled people)
        If entry is human and players guessed it was human → high humanity (human was human)
        If entry is human and players guessed it was AI → low humanity (human seemed AI-like)
        
        Score range: 0-100
        """
```

This feeds into challenge balancing: if AI entries consistently score >80 humanity, the prompts are adjusted to introduce more detectable flaws.

---

## 14. Voting System (Bluff Mode)

### 14.1 Anonymous Presentation

When both entries are ready, the VotingService:

1.  Randomly assigns labels (A or B) to the human and AI entries
2.  Strips all metadata (no timestamps, no origin info)
3.  Pushes both entries to the frontend via WebSocket (`VOTING_READY` event)
4.  Starts a 10-second voting window (no hard time limit, but soft nudge after 10s)

### 14.2 Voting Flow

```
Player sees:
  Challenge: "Invent a product nobody needs. Max 6 words."
  
  Entry A:  "A self-stirring sock you wear while walking."
  Entry B:  "The SnoreSilencer 3000 — silences your partner, not your dreams."
  
  [A is AI]  [B is AI]
```

The player clicks one. The vote is sent via WebSocket (`VOTE_SUBMITTED` event).

### 14.3 Reveal System

After the vote (or after the voting window expires):

1.  WebSocket sends `REVEAL` event with: which entry was human/AI, humanity scores, brief explanation
2.  The frontend shows the reveal animation
3.  The ScoringService calculates and updates the player's rating
4.  The next round begins

---

## 15. Database Architecture

### 15.1 Schema Overview

```
users
  └── id, display_name, guest_id, email, created_at, updated_at

challenges
  └── id, name, interaction_type, prompt, constraints_json, time_limit_seconds,
      input_type, voting_criteria, difficulty, scoring_rules_json,
      ai_prompt_template_id, replayability_json, created_at, updated_at

challenge_daily
  └── date, challenge_id, variant_constraints_json

sessions
  └── id, user_id, challenge_ids_json, started_at, completed_at,
      final_score, rounds_played, is_daily

rounds
  └── id, session_id, challenge_id, round_number,
      human_entry_id, ai_entry_id, vote, reveal_data_json,
      state, started_at, completed_at, time_spent_seconds

entries
  └── id, round_id, author_type, content, submitted_at,
      validity_json, constraint_violations_json

ai_entries  (references entries)
  └── entry_id, provider, model, prompt_version, prompt_hash,
      raw_response, sanitized_response, token_count, generated_at

votes
  └── id, round_id, user_id, selected_entry (A/B), voted_at

scores
  └── id, user_id, round_id, base_score, time_bonus, streak_bonus, total_score, scored_at

detection_ratings
  └── user_id, rating, last_updated

humanity_scores
  └── entry_id, humanity_score, total_votes, last_updated

streaks
  └── user_id, type, count, last_active_date, longest_record

leaderboard_snapshots
  └── date, user_id, score, rank

prompt_audit
  └── id, prompt_version, prompt_template, challenge_id, ai_response,
      provider, sanitized, recorded_at

sessions_websocket  (in-process memory, not in DB)
  └── session_id -> {connected_user_ids, round_state, entries_ready, ...}
```

### 15.2 Key Tables

#### users

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Primary key |
| guest_id | TEXT (unique) | For guest users (stored in localStorage, synced to server) |
| display_name | TEXT | "Player_4829" auto-generated or user-set |
| email | TEXT (nullable) | Optional for account creation |
| detection_rating | REAL | ELO-style rating (default 1000) |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

#### challenges

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT (PK) | e.g., "challenge_slogan_01" |
| name | TEXT | "Tiny Tagline" |
| interaction_type | TEXT | "Quick Text" |
| prompt | TEXT | "Write a slogan for a dragon-owned bakery." |
| constraints | JSON | Array of constraint objects |
| time_limit_seconds | INTEGER | 15 |
| input_type | TEXT | "text_single_line" |
| voting_criteria | TEXT | "most_believable" |
| difficulty | INTEGER | 1-5 |
| scoring_rules | JSON | Base score, multipliers |
| ai_prompt_template_id | TEXT | Foreign key to prompt templates |
| replayability | JSON | Daily variants, constraint pool |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

#### rounds

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| session_id | UUID (FK) | |
| challenge_id | TEXT (FK) | |
| round_number | INTEGER | 1, 2, or 3 |
| human_entry_id | UUID (FK) | |
| ai_entry_id | UUID (FK) | |
| vote | TEXT | "A" or "B" (which entry the player chose as AI) |
| reveal_data | JSON | {human_was: "A"/"B", humanity_human: 0-100, humanity_ai: 0-100} |
| state | TEXT | "writing", "reveal_ai", "voting", "scored" |
| started_at | TIMESTAMP | |
| completed_at | TIMESTAMP | |
| time_spent_seconds | REAL | |

#### prompt_audit

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | |
| prompt_version | TEXT | "v1.0" |
| prompt_template | TEXT | Full system prompt used |
| challenge_id | TEXT (FK) | |
| ai_response | TEXT | Sanitized response stored |
| raw_response | TEXT | Original (for debugging) |
| provider | TEXT | "openai", "anthropic", "stub" |
| token_count | INTEGER | |
| recorded_at | TIMESTAMP | |

### Notes

- All prompts and responses are stored for audit/reproducibility.
- The `sessions_websocket` state is intentionally in-process memory (not SQLite) — it's ephemeral state for WebSocket connection management.
- `challenge_daily` table enables deterministic daily challenge selection by date.
- SQLite runs in WAL mode with `PRAGMA foreign_keys=ON`; generic `JSON` columns are used (not PostgreSQL `JSONB`) for driver portability.

---

## 16. Real-time Communication

### 16.1 WebSocket Events

All real-time game state is communicated via WebSocket. REST is used for static data (challenges, leaderboards, user profile).

| Event | Direction | Payload | When |
|-------|-----------|---------|------|
| `SESSION_START` | Server → Client | `{sessionId, roundCount, challenges: [...]}` | Session begins |
| `ROUND_START` | Server → Client | `{roundNumber, challenge, timeLimit}` | Next round begins |
| `ENTRY_SUBMITTED` | Client → Server | `{sessionId, roundId, entry}` | Player submits answer |
| `AI_RESPONSE_READY` | Server → Client | `{roundId, entries: {A, B}}` | Both entries ready, voting begins |
| `VOTE_SUBMITTED` | Client → Server | `{roundId, vote: "A"\|"B"}` | Player votes |
| `REVEAL` | Server → Client | `{roundId, humanWas: "A"\|"B", humanityHuman, humanityAI, explanation}` | Reveal shown |
| `ROUND_SCORED` | Server → Client | `{roundId, score, ratingChange, streakUpdate}` | Scoring complete |
| `SESSION_END` | Server → Client | `{sessionId, totalScore, accuracy, humanityStats}` | All rounds complete |

### Connection Management

- On frontend connect, the client sends its `guest_id` or `user_id`.
- The WebSocket handler validates the session and subscribes the client to the session's pub/sub channel.
- Each session gets an in-process pub/sub topic (single backend process in the MVP).
- If a client disconnects mid-round, they can rejoin (state is persisted in SQLite; ephemeral state in memory).

---

## 17. Competitive Systems (Future)

Not in MVP. Documented for future expansion:

- **Ranked Mode**: Daily/weekly ranked playlists with ELO.
- **Divisions**: Bronze, Silver, Gold, Platinum, Diamond based on Detection Rating.
- **Placement Matches**: 5 unrated rounds to establish initial rating.
- **Seasonal Resets**: Rating soft-reset each season, with seasonal rewards.

---

## 18. Social Features (Future)

Not in MVP. Documented for future expansion:

- **Community Voting**: Players vote on which AI entry is "most human-like" across all players.
- **Replay Sharing**: Shareable links to replay a round.
- **Challenge Publishing**: Community-submitted challenges (requires moderation).
- **Trust System**: Reputation for challenge creators.

---

## 19. Future Expansion

Nexus maintains the pattern of documenting future systems as reserved architecture. For Man vs. Machine:

| System | Reserved Architecture | Document Reference |
|--------|-----------------------|--------------------|
| **True Multiplayer** | `app/services/multiplayer/` — matchmaker, room service, sync protocol | §10.3, §16 |
| **Visual Challenges** | Input type `sketch`, canvas component, image-based humanity scoring | §12.1, §12.4 |
| **Build Challenges** | Drag-arrangement input, spatial scoring | §12.1, §12.4 |
| **Local LLM Support** | Ollama provider implementation, fallback detection | §13.1 |
| **Mobile App** | PWA-first, then native wrappers | §8, §5 |
| **Tournament Mode** | Bracket generation, live events, scheduling | §17 |
| **Creator Mode** | Community challenge submission + review pipeline | §18 |
| **Corporate Variant** | White-labeled version for training/assessment | §19 |
| **Analytics Dashboard** | Player analytics, AI analytics, challenge analytics | §21 |

### 19.1 True Multiplayer (Future)

```
┌────────────────────────────────────────────┐
│          Matchmaking Service               │
│  Player queues → matched into rooms of 3-6 │
└────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────┐
│          Room Service                      │
│  Manages round state for N players         │
│  Collects entries from all players         │
│  Generates 1 AI entry                      │
│  Broadcasts A/B/C/D entries                  │
│  Collects votes from all players           │
│  Computes consensus + scores               │
└────────────────────────────────────────────┘
```

Each round: `N - 1` humans + 1 AI. Everyone votes on which is AI. Scoring rewards both correct detection and "humanity" (how many people you fooled).

### 19.2 Local LLM Support (Future)

When Ollama is available, the StubProvider is replaced with an OllamaProvider that:
- Downloads the model on first use
- Runs entirely on the user's machine (no provider API calls)
- Falls back to the stub pool if the model fails

This enables offline play and removes the provider dependency.

---

## 20. Agent Development Guidelines

### Operating Contract

These guidelines prevent architectural drift and ensure the web-first, micro-challenge, social-deduction design is preserved.

1.  **Read the docs first.** Always read `docs/01_Master_Architecture.md`, the relevant section of `docs/02_Implementation_Guide.md`, and `docs/04_Game_Design_Document.md` before writing any code.
2.  **Complete only the current sprint's scope.** Do not add features, refactor, or "improve" code outside the current sprint's acceptance criteria.
3.  **Preserve the AI fairness constraint.** The AI must receive the same prompt as the human. Never add AI-only instructions that would make it obviously identifiable.
4.  **Time asymmetry is non-negotiable.** The AI has unlimited time; the human has 15–60 seconds. Do not add AI time limits that would make the game trivially easy.
5.  **No raw prompt leakage.** The AI system prompt must never mention being an AI or reference game rules. Enforce this in ContentFilter.
6.  **Challenges are data.** Never hardcode challenge logic. All prompts, constraints, time limits, and scoring rules come from the challenge definition files in `app/data/challenge_library/`.
7.  **Web-first, no native app.** The MVP is a browser application. Do not add Tauri/Electron/React Native wrappers.
8.  **One responsibility per module.** Each service, repository, and component does exactly one thing.
9.  **Business logic belongs in the backend.** The frontend is a thin presentation layer. No scoring logic, no constraint validation, no entry anonymization in the frontend.
10. **WebSocket state is authoritative.** The round state, entries, votes, and reveal are managed server-side. The frontend is a passive display. Clients cannot forge votes or skip states.

---

## 21. Testing Strategy

### Backend Tests (pytest + pytest-asyncio)

| Test Module | Focus |
|-------------|-------|
| `test_challenge_engine.py` | Constraint validation, time limit calculation, daily rotation, input validation |
| `test_ai_service.py` | Prompt construction, provider selection, fallback logic, response sanitization |
| `test_content_filter.py` | Prompt injection detection, meta-mention rejection, length validation |
| `test_voting.py` | Anonymization (A/B randomization), vote processing, reveal generation |
| `test_scoring.py` | Round score calculation, ELO rating updates, humanity score computation, streak tracking |
| `test_session.py` | State machine transitions, round orchestration, session lifecycle |
| `test_websocket.py` | Event dispatching, connection management, pub/sub |
| `test_e2e.py` | Full flow: challenge → human entry → AI entry → vote → reveal → score |

### Frontend Tests (Vitest)

| Test Module | Focus |
|-------------|-------|
| `Timer.test.tsx` | Countdown display, urgency color shift, auto-submit |
| `VotingScreen.test.tsx` | Entry display, A/B randomization, vote submission |
| `RevealScreen.test.tsx` | Correct reveal, humanity display, score animation |
| `ChallengeView.test.tsx` | Prompt display, constraint rendering |
| `EntryInput.test.tsx` | Text input, constraint validation feedback |

### Test Fixtures

| File | Purpose |
|------|---------|
| `backend/tests/fixtures/challenges/` | Sample challenge definitions in JSON |
| `backend/tests/fixtures/ai_responses/` | Sample AI responses for testing sanitization |
| `frontend/tests/fixtures/` | Mock WebSocket events, sample entries |

### E2E Test Flow

`backend/tests/test_e2e.py` walks all 13 steps of Implementation Guide §12.4
(StubProvider, no API keys): start backend → session start (3 challenges) →
WebSocket connect → ROUND_START → submit entry → AI_RESPONSE_READY
(anonymized A/B, own entry unlabelled) → VOTE/VOTE_CONFIRMED → REVEAL
(attribution + humanity) → ROUND_SCORED (score + rating) → round 3 →
SESSION_END (summary) → leaderboard + profile → share result + replay link.

    pytest tests/test_e2e.py -v

---

## 22. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-08-03 | Initial draft. Based on analysis of idea.md and idea2.md. Defines the micro-first, web-first, social-deduction architecture. |
| 1.1 | 2026-10-01 | Delivery model changed to a local-first web dashboard: SQLite replaces PostgreSQL, in-process state replaces Redis, Docker Compose removed. Hosted deployment (PostgreSQL/Redis/Nginx) deferred to post-MVP. Game rules, AI fairness constraints, and challenge engine unchanged. |
| 1.2 | 2026-10-01 | Auth implementation details: PyJWT added to the backend stack (HS256 access tokens); users gained a nullable `password_hash` column (migration 002) for email/password accounts — hashing uses stdlib PBKDF2-HMAC-SHA256 (passlib is unmaintained and was never in §8). Added `GET /auth/me` protected endpoint. |
| 1.3 | 2026-10-08 | Sprint 8 implemented per spec: ContentFilter (meta-mention/injection/leakage patterns, 500-char cap) and PromptAuditService (version-keyed templates, `AI_PROMPT_VERSION` active version, audit recording of raw + sanitized responses). No interface changes to the documented contracts; `record_usage` takes optional `raw_response`/`prompt_version` beyond the guide's signature. |
| 1.4 | 2026-10-08 | Sprint 9 implemented per spec, plus Ollama. Provider ABC gained an optional keyword-only `challenge_id` (StubProvider needs it to pick its pool; external providers ignore it). New `OllamaProvider`: local LLM option per Scope Constraint §3.1.7, chain is OpenAI → Anthropic → Ollama → Stub, `think:false` is sent unconditionally (qwen3-family models otherwise return empty output). Chain build/selection lives in `providers/__init__.py` (`build_provider_chain`, `select_provider`). Config: `OLLAMA_ENABLED`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (default `qwen3.5:9b`, winner of the local bake-off on a 4GB-VRAM machine). |
| 1.5 | 2026-10-08 | Sprint 10 implemented per spec. AIService orchestrates the §13.1 pipeline: prompt build (v1.0 template + per-challenge `aiPromptGuidance` appended to the system prompt), provider-chain walk with failure/dirty-response fall-through and `retry_on_injection`, ContentFilter sanitization before storage, and audit recording of raw + sanitized responses. `POST /voting/submit-entry` (Implementation Guide §2.7) validates the human entry — hard violations block — and returns both entries. New config `OLLAMA_TIMEOUT` (default 120s) so a busy GPU degrades to StubProvider. Round/entry persistence and the vote endpoint remain Sprint 11/13 scope. |
| 1.6 | 2026-10-08 | Sprint 11 implemented per spec. VotingService: seeded-per-round A/B assignment (stable within a round, varying across rounds — one assignment source shared by presentation and reveal), vote recording, reveal with attribution + explanation, and retroactive humanity scoring (share of voters who guessed each entry was human) persisted to `humanity_scores` and mirrored into `rounds.reveal_data`. `POST /voting/vote` records the vote and returns the reveal in one response; re-votes/re-reveals return 409. Note: `reveal()` builds `reveal_data` as a complete replacement (repo semantics from Sprint 3), so any later writer must pass all keys. |
| 1.7 | 2026-10-08 | Sprint 12 implemented per spec. ScoringService: §12.5 round score with component breakdown, ELO Detection Rating per GDD §6.2 (K=32 below 50 scored rounds, 16 after; floor 100; AI rating mapped from humanity as `1000 + (humanity - 50) * 4`), humanity recomputation deriving the entry letter from `reveal_data`, correct-guess and daily streaks. LeaderboardService: daily board ranked by score (accuracy from the score's base component), all-time ranked by rating (accuracy from `reveal_data.vote_correct`), idempotent daily snapshots. `GET /leaderboard/daily|all-time` are public reads. Scoring tension resolved: the GDD §6.1 "wrong guess: 0" row is the guess component, not the whole round (Implementation Guide §5.4 documents it). |
| 1.8 | 2026-10-08 | Sprint 13 implemented per spec. SessionService is the composition root for a round: state machine `writing` → `reveal_ai` → `voting` → `scored` (invalid transitions rejected, DB-verified), entry + AI generation + anonymized A/B presentation, and the Sprint 12 scoring composition (Score row, ELO rating, streaks) on vote. Sessions run 3 rounds then complete; the summary reports totals, accuracy, and the per-round breakdown. New endpoints: `POST /session/{id}/rounds/{round_id}/entry`, `POST /session/{id}/next`; `/voting/vote` now returns reveal + score; `/session/start` creates round 1; `/voting/submit-entry` stays the stateless practice path. Session-scoped calls enforce ownership (404 for foreign sessions). Note: summary `rating_change` stays null — computing it needs a session-start rating snapshot, which the MVP schema has no column for (documented in Implementation Guide §5.5). |
| 1.9 | 2026-10-08 | Sprint 14 implemented per spec. WebSocket layer at `/ws/session/{session_id}?token=...`: auth before accept (invalid token or foreign session → 403 handshake rejection), per-session pub/sub in `WebSocketManager` (broadcasts reach every socket on the session topic; dead sockets are dropped), and handlers driving SessionService for SUBMIT_ENTRY / VOTE / PING. Connect sends SESSION_STARTED + ROUND_START for the current round, so reconnects resume from SQLite; a finished session replays SESSION_END. **Dependency fix: `websockets>=12.0` installed and added to §8's realized stack** — it was listed in §8 from the initial draft but never installed, so uvicorn could not upgrade WebSocket requests at all. |
| 1.10 | 2026-10-08 | Sprint 15 implemented per spec. Frontend scaffolding on top of Sprint 1's skeleton: React Router v6 with all 7 routes inside a shared nav layout, Tailwind CSS with the shadcn/ui token theme, hand-authored shadcn/ui primitives (Button, Card, Input, Badge), Axios client (`src/api/client.ts`, base URL + JWT interceptor), ESLint/Prettier/Vitest+jsdom toolchain. Notes: the ESLint config is `.eslintrc.cjs` (the package is `"type": "module"`, so ESLint 8 cannot read a `.js` config); the real-time client uses the browser's native WebSocket rather than §8's Socket.IO Client (the backend speaks raw JSON frames — no extra dependency). |
| 1.11 | 2026-10-08 | Sprint 16 implemented per spec. Typed API client modules for all 7 resource groups over the Axios instance (auth, challenges, session, voting, leaderboard, profile, share), plus `toApiError` normalizing error payloads (401/404/400-violation/500) into `{status, message, details}` for components. Shared TypeScript types mirror the backend schemas one-to-one; note the three casing conventions: challenge definitions use the file format's camelCase, REST responses use snake_case, and WebSocket event payloads use camelCase. |
| 1.12 | 2026-10-08 | Sprint 17 implemented per spec. AuthContext + useAuth: auto guest-login on first visit (resuming the persisted guest_id), stored-token validation via `/auth/me` on load, login/register/guest actions, and logout that survives reloads (a `loggedOut` marker prevents auto-guest from undoing it). A `RequireAuth` guard gates the signed-in routes; Home and /auth stay public. A `path="*"` NotFound route exists because React Router v6 renders nothing for the whole layout branch on unmatched URLs. |
| 1.13 | 2026-10-08 | Sprint 18 implemented per spec. ChallengeView/Timer/EntryInput/StreakBadge/RatingDisplay with useTimer (deadline-based countdown, urgency states) and useChallenges (daily lookup, definitions, server validation). A client-side `src/lib/constraints.ts` mirrors the backend ConstraintEngine for live feedback on the browser-checkable constraint types; the server remains authoritative on submission, and heuristic constraints (must_rhyme, no_adjectives) stay backend-only. Vitest runs with `fileParallelism: false` because test files share the module-level API client. |
| 1.14 | 2026-10-08 | Sprint 19 implemented per spec. WebSocket client layer: typed events (`websocket/events.ts`), `SessionSocket` (`websocket/client.ts`) with an injectable socket factory, and `useVoting` owning the connection lifecycle and event→state mapping. VotingContext (entries/vote/reveal) and ScoringContext (score/ratingChange/streak/summary) share one channel via nested providers. VotingScreen shows anonymized A/B entries with vote buttons, no origin hints, and a 10-second soft-nudge window that never locks voting. Note: the sprint text's `VOTE_SUBMITTED` event name drifted from the implementation — the server (Sprint 14) accepts `VOTE`, and the client matches it. |
| 1.15 | 2026-10-08 | Sprint 20 implemented per spec. RevealScreen (attribution, both entries labeled yours/AI, humanity 0-100 bars with clamping + progressbar a11y, explanation), ScoreAnimation (count-up to the total with the base/time/streak breakdown), SessionSummary (totals + per-round breakdown + play again), `useScoring`, and `websocket/hooks.ts` (`useRoundState` phase derivation, `useSessionEvents` session lifecycle). The Session page renders the full loop: writing → voting → reveal+score → summary. The REVEAL wire event does not carry entry text, so the client merges the round's entries into the reveal payload for display. |
| 1.16 | 2026-10-10 | Sprint 21 implemented per spec. SessionContext round state machine (`idle → writing → voting → reveal_ai → score → complete`) + `useSession` loop orchestration: optimistic entry into `writing` from the session-start REST response, one-shot 2.5s score dwell with a per-round-id stale-score guard (a finished round's leftover score can no longer re-enter the state machine), round-clock auto-submit at expiry, and per-state rendering. 110 frontend tests (SessionContext + SessionClock suites added; fake timers limited to Date/setTimeout/setInterval so the round clock does not starve React's act queue). |
| 1.17 | 2026-10-10 | Sprint 22 implemented per spec, **plus a backend gap it exposed**. Leaderboard + Profile pages: `LeaderboardTable` (sortable rank/player/score-or-rating/accuracy, nulls last, aria-sort), `useLeaderboard`, Daily/All-time tabs, `HumanityMeter` (0-100 clamped progressbar), Profile page (rating/rounds/accuracy/streaks + Chart.js humanity trend + display-name rename), `StreakBadge` in the nav. The sprint said "Backend Changes: None", but Implementation Guide §2.5's `GET/PUT /profile` endpoints never existed (Sprint 16's client had never been verified live): added `app/api/v1/profile.py`, `ProfileService`, `ScoringRepository.get_recent_humanity_scores`. `chart.js@4.4.0` added to §8's realized stack (sanctioned there). |
| 1.18 | 2026-10-10 | Sprint 23 implemented per spec. Settings page: AI provider dropdown (OpenAI/Anthropic/Stub), dark-mode switch, sound-effects switch. `useSettings` + `SettingsProvider` persist `{ theme, aiProvider, soundEnabled }` to localStorage with validated reads + corrupt-JSON fallback; `ThemeProvider` toggles the `dark` class on `<html>` (Tailwind `darkMode:['class']` and the globals.css `.dark` tokens shipped in Sprint 15 but had no toggler until now). The title's "Content Filter Integration" needed no work — ContentFilter has been wired into AIService since Sprints 8/10. |
| 1.19 | 2026-10-10 | Sprint 24 implemented per spec. `tests/test_e2e.py` walks Implementation Guide §12.4's full flow (all 13 steps, step 13 added once Sprint 25 landed) over the real HTTP + WebSocket stack with StubProvider: guest → session start → connect → submit → anonymized A/B → vote → reveal → score → summary → leaderboard → profile → share + replay. Added `tests/conftest.py` (shared throwaway-DB / StubProvider client + fixture loaders) and `tests/fixtures/{challenges,ai_responses}/`. **Suite-stall bug found and fixed test-side**: three TestClients in one process hung — `app.websocket.manager` is a module-level singleton whose `asyncio.Lock` binds to the first event loop that awaits it while each TestClient runs its own loop in its own thread, so once that loop dies later broadcasts block forever. The E2E suite now shares ONE module-scoped TestClient (no backend change; cut the suite ~2.4s → ~1.3s). Worth a future sprint: make the manager loop-safe with a lazy lock. |
| 1.20 | 2026-10-10 | Sprint 25 implemented per spec. ShareService (`generate_share_text` in the documented format, `create_share_link`, `generate_share_image`), `POST /api/v1/share/result` (text + link + base64 PNG; 400 unfinished, 404 foreign, 401 unauth) and `GET /api/v1/share/s/{id}` (resolves a shared link to the result text + attributed rounds). Frontend `useShare` (post/copy/download), `ShareButton` (Copy + Download + link dialog), `ResultCard` (score, accuracy, averaged humanity meters) wired onto the Session page. **Doc conflict resolved**: the sprint plan said "PNG via PIL", but §8 sanctions `html2canvas` for result-card images and does not list Pillow (also not installed) — the server-side card is rasterised with the standard library only (`zlib` + `struct` + a compact 5x7 bitmap font), so the documented backend contract holds with no new native dependency. Shared links are unobfuscated session ids and auth-gated; a `shares` table is post-MVP. |
| 1.21 | 2026-10-10 | Sprint 26 implemented per spec. `app/scripts/challenge_data.py` is the single load path (`library_ids`, `read_definitions`, `load_challenge_library`) shared by the data migration, the standalone script, and the app's startup `sync_library_to_db`, so all three agree on what "loaded" means. Alembic `003_load_challenges` inserts the 25 definitions idempotently (the plan named 002, which the password_hash migration already owned). `scripts/load_challenges.py` sits at the repo-root script dir where `dev.py` already lives (the plan said `backend/scripts/`). `tests/test_challenge_data.py` covers the acceptance criteria incl. 25 consecutive days covering all 25 challenges exactly once. Migration 003 pre-populates `challenges`, which broke the hand-seeded fixtures in `test_share.py`/`test_profile.py` (PK collision) — both now check for an existing row first. |
| 1.22 | 2026-10-10 | Sprint 27 implemented per spec (**final build sprint — MVP complete**). Single-port release mode: `main.py` serves the built frontend on the API port, with `/` and any non-reserved browser path returning index.html (SPA fallback), build files served from `frontend/dist`, a missing `/assets/*` bundle 404ing rather than silently returning the shell, and the `api`/`ws`/`docs`/`redoc`/`openapi.json`/`health` prefixes never claimed so a typo'd API path returns a JSON 404. `FRONTEND_DIST_DIR` is resolved per request (no import-time snapshot). The health check moved `/` → `/health` so `/` can serve the app. Frontend: `.env.production` sets `VITE_API_BASE_URL=/api/v1` (same-origin release) and `toWebSocketUrl` resolves a relative base against `window.location`, picking ws/wss from the page protocol. Added `.github/workflows/ci.yml` (ruff, mypy, pytest + tsc, eslint, prettier, vitest, build), `backend/scripts/run.sh`, `frontend/scripts/build.sh`. Docker/Nginx production deployment remains post-MVP. |
| 1.23 | 2026-10-10 | Sprint 28 (documentation finalization) — all five docs + AGENTS.md updated to final status/version: Master §22 changelog extended through the MVP, Implementation Guide refreshed (release-mode section, camelCase WS payload correction, final test inventory), README rewritten. No code changes. Final state: 277 backend + 157 frontend tests green; ruff/mypy/tsc/eslint/prettier clean. |
| 1.24 | 2026-10-10 | **Owner-approved addition: PyInstaller desktop bundling.** §8 gains a Build/Packaging row for PyInstaller 6.11+ as a build-time-only tool (not a runtime dependency — the app still runs on plain FastAPI + SQLite + the Vite output). Adds `packaging/launcher.py` (frozen entry point: boots uvicorn, points `MANVSMACHINE_FRONTEND_DIST` at the bundled UI, keeps SQLite beside the executable instead of the temp unpack dir, opens the browser), `packaging/manvsmachine.spec` (collects alembic + migrations, `app/data` challenge library and stub pools, and `frontend/dist`; hidden imports for uvicorn's lazily-loaded websocket protocols), and `scripts/build_executable.py`. `main.py` gained `MANVSMACHINE_FRONTEND_DIST` so a frozen `__file__` (which resolves outside the repo) can still find the bundled frontend. Result: a ~38 MB double-click bundle verified end-to-end — UI, API, WebSocket game (3 rounds), share card, and replay all work with **no Python and no Node on the machine**. |

---

Appendix A: API Reference (Summary)

> Full API reference is in `docs/02_Implementation_Guide.md` Section 2. Brief summary:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/auth/guest` | Create/get guest session |
| POST | `/api/v1/auth/register` | Email/password account |
| POST | `/api/v1/auth/login` | Login with email/password |
| GET | `/api/v1/auth/me` | Protected profile for the token holder |
| GET | `/api/v1/challenges/daily` | Get today's daily challenge |
| GET | `/api/v1/challenges/{id}` | Get a specific challenge definition |
| POST | `/api/v1/challenges/validate` | Pre-submission constraint check |
| POST | `/api/v1/session/start` | Start a session (creates round 1) |
| GET | `/api/v1/session/{id}` | Session state |
| GET | `/api/v1/session/{id}/summary` | Totals, accuracy, per-round breakdown |
| POST | `/api/v1/session/{id}/next` | Advance to the next round / complete |
| POST | `/api/v1/session/{id}/rounds/{round_id}/entry` | Submit a round entry (REST path) |
| POST | `/api/v1/voting/submit-entry` | Stateless practice: validate + AI generation |
| POST | `/api/v1/voting/vote` | Record a vote; returns the reveal + score |
| GET | `/api/v1/leaderboard/daily` | Today's board by score |
| GET | `/api/v1/leaderboard/all-time` | All-time board by Detection Rating |
| GET | `/api/v1/profile` | Profile + stats + recent humanity |
| PUT | `/api/v1/profile` | Update display name |
| POST | `/api/v1/share/result` | Text + PNG result card for a finished session |
| GET | `/api/v1/share/s/{session_id}` | Resolve a shared result link |
| WS | `/ws/session/{session_id}` | WebSocket for real-time round flow |
| GET | `/health` | Health check |
| GET | `/` (and non-API paths) | Built frontend in release mode (SPA fallback) |

Appendix B: Future Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| MVP | Quick Text mode, local web app (SQLite), 25 challenge templates | **Shipped** (Sprint 27) |
| Phase 2 | Weekly challenges, 100+ templates, richer result-card imagery (client-side `html2canvas`) | Future |
| Phase 3 | True multiplayer (2+ humans + voting), Visual/Build/Explain challenge types | Future |
| Phase 4 | Tournaments, Creator mode, Battle Pass | Future |
| Phase 5 | Native mobile apps, hosted deployment (PostgreSQL/Redis/Nginx) | Future |

Local LLM support (Ollama) and result-card image generation are **not** Phase 5
items — both shipped inside the MVP (Sprint 9 and Sprint 25 respectively).

---

*This is Document 1 of 5. For the game design experience, see `docs/04_Game_Design_Document.md`. For implementation details, see `docs/02_Implementation_Guide.md`. For the challenge catalog, see `docs/05_Micro_Challenge_Library.md`. For the build roadmap, see `docs/03_Sprint_Plan.md`.*
