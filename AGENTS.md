# AGENTS.md — Man vs. Machine Project Rules

> **Version:** 1.2
> **Status:** Draft — Sprint 0 (Pre-MVP)
> **Purpose:** Operating contract for AI coding agents working on Man vs. Machine
> **Read:** `docs/01_Master_Architecture.md` fully before starting any work.

These rules are derived from the Project Rules (Section 3) and Scope Constraint (Section 3.1) of the Master Architecture.

---

## Core Rules

1. **Challenges are data, not code.** All challenge definitions (prompts, constraints, time limits, scoring rules) live in `backend/app/data/challenge_library/` as JSON files. Adding a new challenge requires zero code changes.
2. **The AI gets the same prompt as the human.** Never add AI-only instructions that would make it obviously identifiable. The AI prompt is a deterministic transformation of the challenge definition.
3. **Time asymmetry is the game mechanic.** The AI has unlimited time; the human has 15–60 seconds. Do not add AI time limits that would make the game trivially easy.
4. **No raw prompt leakage.** The AI system prompt must never mention being an AI, nor reference the game's rules, nor acknowledge the human competitor. Enforce this in `ContentFilter`.
5. **Humanity is measurable and transparent.** Every entry (human or AI) receives a humanity score (0–100). This feeds into challenge balancing and player ratings.
6. **Every feature must be testable independently.** No feature is deployed without unit or integration tests.
7. **Business logic belongs in backend services.** The frontend is a thin presentation layer. All game logic, scoring, AI orchestration, constraint validation, and entry anonymization live in Python services.
8. **One responsibility per module.** Each service, repository, and component does exactly one thing.
9. **Real-time state is authoritative.** The round state, entries, votes, and reveal are managed server-side via WebSocket + in-process state. Clients cannot forge votes or skip states.
10. **Provider fallback is mandatory.** If the primary AI provider fails, fall back to the secondary provider. If all providers fail, use the StubProvider. The game must never break.

### Scope Constraint

1. The game is **NOT** about beating the AI. The core mode is social deduction: guessing which entry is AI.
2. No open-ended long-form challenges in MVP. All MVP challenges are **Quick Text** (15–60 seconds). Visual, Build, Explain, Strategy modes are post-MVP.
3. **No real-time multiplayer in MVP.** All MVP rounds are human-vs-AI. True multiplayer is post-MVP.
4. **No user-generated content in MVP.** The Micro Challenge Library is curated, not community-submitted.
5. **No monetization in MVP.** The MVP is completely free.
6. **Web-first, local-first, no desktop app.** The game runs in the browser against a local FastAPI server with SQLite (no Docker required). No Tauri/Electron/React Native wrappers. Hosted deployment is post-MVP.
7. **AI providers are external services.** The system uses provider APIs (OpenAI, Anthropic). Local LLM support (Ollama) is a configuration option, not the primary path.
8. **The AI prompt must be auditable.** Every AI prompt used in a round is stored in the `prompt_audit` table and versioned.
9. **Prompt injection protection.** AI responses are sanitized before presentation. No unfiltered LLM output reaches the UI.

---

## Sprint Execution Workflow

Every sprint follows the same loop: **plan → scope → implement → verify → commit → worklog.**

1. **Plan & scope.** Read the sprint's section in `docs/03_Sprint_Plan.md` (including Inputs/Outputs/Acceptance Criteria), the relevant section(s) of `docs/02_Implementation_Guide.md`, and `docs/01_Master_Architecture.md` §20 (Agent Development Guidelines). Review the sprint's Files Created/Modified before starting and record the agreed scope in the sprint's `worklog.md` entry.
2. Create/modify **only** the files listed in the sprint
3. Write tests first (TDD): write the test, run it, see it fail, implement, see it pass
4. Run linting and type checking (`ruff`, `mypy`, `tsc`)
5. Verify **all** acceptance criteria manually
6. Update the sprint plan changelog with what was accomplished
7. Update documentation if the change affects specs
8. **Commit** with a descriptive message (`Sprint N: ...`); push to `origin` if the remote is reachable
9. **Update `worklog.md`** with one entry per sprint: plan/scope, what was implemented, verification results (tests, lint, acceptance criteria), commit reference(s), and any notes or deviations

---

## Agent Development Guidelines

- **Complete only the current sprint's scope.** Do not add features, refactor, or "improve" code outside the current sprint's acceptance criteria.
- **Do not add future features early.** YAGNI (You Aren't Gonna Need It) applies. No multiplayer, no Visual/Build challenges, no monetization, no native app.
- **Never refactor unrelated code during a sprint.** If you see something that could be improved, note it and continue with the current sprint's scope.
- **Keep changes localized to the relevant modules.** If you need to touch a file not listed in the sprint, document it as a note and flag it.
- **Ensure all acceptance criteria pass before moving to the next sprint.** No exceptions.
- **Preserve the AI fairness constraint.** The AI prompt must be a deterministic transformation of the challenge definition. No hidden instructions.
- **Web-first.** Never add Tauri/Electron/React Native wrappers.
- **Test first.** Write the test, watch it fail, implement the code, watch it pass.
- **Run linting and type checking** before considering a sprint done.

---

## Prohibited Actions

- Adding dependencies not specified in `docs/01_Master_Architecture.md` §8 (Technology Stack)
- Refactoring code outside the current sprint's scope
- Hardcoding challenge logic — all prompts, constraints, time limits, and scoring rules must come from JSON definition files
- Making the AI response identifiable (e.g., adding AI-only instructions, mentioning "as an AI", referencing system prompts)
- Transmitting user data to external services (no analytics, no telemetry)
- Using "TODO" or "FIXME" comments as a substitute for implementation
- Creating native desktop or mobile apps (no Tauri, Electron, React Native)
- Implementing user-generated content or community challenge submission
- Adding monetization, paywalls, or cosmetics shops
- Implementing Visual, Build, Explain, or Strategy challenge types (post-MVP)
- Implementing true multiplayer (2+ humans + voting) — post-MVP

---

## Testing Requirements

- Every sprint must have tests written or updated
- Backend: `pytest` with `pytest-asyncio`, coverage >= 80% for new code
- Frontend: `vitest`, coverage >= 75% for new components
- E2E tests: Full flow from session start through 3 rounds to session summary, using `StubProvider` (no real AI API keys needed)
- All tests must pass before a sprint is marked "Done"
- Test fixtures for challenge definitions live in `backend/tests/fixtures/challenges/`
- Test fixtures for stub entries live in `backend/tests/fixtures/stub_entries/`
- Run tests with: `cd backend && pytest -v --cov=app`
- Run frontend tests with: `cd frontend && vitest run`
- E2E test flow: start backend with `STUB_PROVIDER_ONLY=true`, run `pytest tests/test_e2e.py -v`

---

## Code Style

### Backend (Python)

- PEP 8 with 4-space indentation
- Type hints required (pydantic models, function signatures)
- Docstrings for all classes and public methods
- `pytest` + `pytest-asyncio` for testing
- `ruff` for linting
- `mypy` for type checking
- Async-first: use `async def` for all service and repository methods that hit the database

### Frontend (TypeScript + React)

- Prettier formatting (2-space indent, single quotes, no semicolons)
- ESLint with React rules
- TypeScript strict mode
- `shadcn/ui` components as base
- `tailwindcss` for styling
- `vitest` for testing
- React Context for global state (SessionContext, VotingContext, ScoringContext, AuthContext)

---

## File Naming Conventions

| Layer | Convention | Example |
|-------|-----------|---------|
| Backend Python modules | `snake_case.py` | `challenge_service.py`, `voting_service.py` |
| Backend classes | `PascalCase` | `ChallengeService`, `VotingService` |
| Backend API routers | `snake_case.py` in `v1/` | `challenges.py`, `voting.py` |
| Frontend components | `PascalCase.tsx` | `VotingScreen.tsx`, `Timer.tsx` |
| Frontend hooks | `useCamelCase.ts` | `useSession.ts`, `useVoting.ts` |
| Frontend contexts | `PascalCase.tsx` | `SessionContext.tsx`, `AuthContext.tsx` |
| Frontend types | `PascalCase.ts` | `challenge.ts`, `session.ts` |
| Challenge definitions | `snake_case.json` | `challenge_slogan_01.json` |
| Database tables | `snake_case` | `users`, `challenges`, `rounds` |
| Tests | `test_*.py` or `*.test.tsx` | `test_scoring.py`, `VotingScreen.test.tsx` |

---

## Documentation Update Protocol

When a sprint changes the architecture or API:

1. Update `docs/02_Implementation_Guide.md` if the change affects technical specs (schema, API contracts, service interfaces)
2. Update `docs/01_Master_Architecture.md` if the change affects architecture decisions (Section 22 Changelog)
3. Add a changelog entry to the relevant sprint in `docs/03_Sprint_Plan.md`
4. Update `AGENTS.md` if the change affects project rules

All docs follow the numbering:
- `docs/01_Master_Architecture.md` — Architecture overview
- `docs/02_Implementation_Guide.md` — Technical reference (schemas, APIs, services)
- `docs/03_Sprint_Plan.md` — Sprint roadmap
- `docs/04_Game_Design_Document.md` — Gameplay experience
- `docs/05_Micro_Challenge_Library.md` — Challenge definitions

---

## Development Commands

```bash
# Backend
cd backend
pip install -e .
uvicorn app.main:app --reload  # dev server on 127.0.0.1:8000

# Frontend
cd frontend
npm install
npm run dev  # Vite dev server on 127.0.0.1:5173

# Full stack (local, no Docker)
python scripts/dev.py  # backend on 127.0.0.1:8000 + frontend on 5173, SQLite auto-initialized

# Tests
cd backend && pytest -v --cov=app
cd frontend && vitest run

# E2E (StubProvider only, no API keys)
cd backend && STUB_PROVIDER_ONLY=true pytest tests/test_e2e.py -v

# Linting/checks
cd backend && ruff check app/ && mypy app/
cd frontend && npx tsc --noEmit && npx eslint src/
```