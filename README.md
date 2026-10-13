# Man vs. Machine

> A micro-challenge game where you and an AI answer the same prompt — and your job is to spot which answer the machine wrote.

**Fire baked. Dragon approved.** — *Entry A*
**Where every loaf is forged in flame.** — *Entry B*

One of those is yours, written in 15 seconds. The other was written by an AI with unlimited time. Can you tell which is which?

## How it plays

1. A challenge drops: *"Write a slogan for a dragon-owned bakery. Max 5 words."*
2. You write your answer against a visible countdown (15–60 seconds).
3. The AI — given the **exact same prompt and constraints**, but unlimited time — writes its own.
4. Both answers appear anonymously as **Entry A** and **Entry B**. You vote: which one is the AI?
5. Reveal. Score. Humanity ratings. Next round.

A session is 3 rounds (~2 minutes), Wordle-style. The game is not "can you out-write the AI" — it's social deduction: the AI is deliberately instructed to write with human imperfections, and over time the system tracks whether players systematically misattribute polished or sloppy answers.

## Status

**MVP complete** — all 27 build sprints done (see [worklog.md](worklog.md)). Playable locally, no Docker, no AI API keys.

- 25 challenges (JSON library), deterministic daily rotation
- Full game loop: challenge → entry → anonymized A/B → vote → reveal → score → rating → streaks → leaderboard → profile → share
- WebSocket game channel with SQLite-authoritative state (reconnect-safe)
- React UI: session flow, leaderboard, profile, settings (light/dark), share cards
- AI provider fallback chain (OpenAI → Anthropic → Ollama → Stub), content filter + prompt audit
- **434 tests passing** (277 backend + 157 frontend) · ruff + mypy + tsc + eslint clean

## Quickstart

```bash
# 1. Python deps (from the repo root)
python -m venv .venv
.venv/Scripts/pip install -e "backend[dev]"     # Windows
# .venv/bin/pip install -e "backend[dev]"       # Linux / macOS

# 2. Frontend deps
cd frontend && npm install && cd ..

# 3. Play (dev: backend :8000 + Vite :5173, hot reload)
.venv/Scripts/python scripts/dev.py
```

| URL | What |
|-----|------|
| http://localhost:5173 | The game (dev) |
| http://127.0.0.1:8000/docs | Swagger UI — try the API |

### One-port release mode

Build the UI into the backend and serve everything from `:8000`:

```bash
bash frontend/scripts/build.sh   # vite build → frontend/dist
bash backend/scripts/run.sh      # uvicorn serves API + WebSocket + UI
```

Then open <http://127.0.0.1:8000>. `frontend/.env.production` points the built
UI at the same origin (`/api/v1`), so no CORS or second port is involved.

No AI API keys are required: without keys the game runs on the built-in StubProvider. To use real models, set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `backend/.env`. Other settings: `DATABASE_URL`, `JWT_SECRET_KEY`, `STUB_PROVIDER_ONLY=true`, `OLLAMA_ENABLED`/`OLLAMA_MODEL` (local LLM).

## Tests

```bash
cd backend && ../.venv/Scripts/python -m pytest -v --cov=app
cd frontend && npm run test
```

CI runs the same checks on every push (`.github/workflows/ci.yml`): ruff, mypy,
pytest, tsc, eslint, prettier, vitest, and the production build.

## Project layout

```
backend/app/
  api/v1/            REST routers (auth, challenges, session, voting, leaderboard, profile, share)
  scripts/           challenge-library loader shared by migration + script + startup
  core/              config, security (JWT/PBKDF2), exceptions, in-process state
  db/                SQLModel models, async SQLite connection, Alembic migrations
  data/              challenge_library/ (25 JSON) · stub_entries/ (25 pools) · ai_prompts/
  repositories/      data access layer
  services/          challenge engine, constraint engine, scoring, voting, share, profile
  websocket/         live session channel (WebSocketManager + handlers)
frontend/src/
  components/        ChallengeView, VotingScreen, RevealScreen, ResultCard, ShareButton, …
  contexts/          Auth, Voting, Scoring, Session
  hooks/             useSession, useVoting, useChallenges, useLeaderboard, useShare, useSettings
  api/               typed API client (axios) + error normalisation
scripts/             dev.py (one-command dev) · load_challenges.py (library load)
docs/                architecture, implementation guide, sprint plan, game design, challenge library
worklog.md           sprint-by-sprint build journal
```

## Design principles

- **The AI gets the same prompt as the human.** No hidden instructions, ever — the AI prompt is a deterministic transformation of the challenge definition and fully audited.
- **Time asymmetry is the game.** The AI has unlimited time; you have 15–60 seconds. That's the whole tension.
- **Challenges are data, not code.** Every challenge lives as JSON; adding one requires zero code changes.
- **No raw prompt leakage.** AI responses are sanitized before they reach the UI.
- **Business logic lives in the backend.** The frontend is a thin presentation layer.
