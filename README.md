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

Pre-MVP, built sprint-by-sprint (see [worklog.md](worklog.md)):

| Done | Sprint |
|------|--------|
| ✅ | Local-first scaffolding — FastAPI + SQLite, one-command dev script, **no Docker** |
| ✅ | Full database schema (13 tables, Alembic migrations) |
| ✅ | Six repositories (users, challenges, sessions, voting, scoring, prompt audit) |
| ✅ | JWT auth — instant guest mode, optional email/password accounts |
| ✅ | Content catalog — 25 challenges, 250 hand-written stub entries, versioned AI prompt template |
| ✅ | Challenge engine — constraint validation (hard/soft), scoring, deterministic daily rotation |
| ✅ | REST API — daily challenge, sessions, entry validation |
| 🔜 | Content filter + prompt audit, AI provider layer, voting & scoring services, WebSocket game loop, React frontend |

**79 tests passing** · ruff + mypy + tsc clean.

## Tech stack

- **Backend:** Python 3.11+, FastAPI, SQLModel/SQLAlchemy (async), SQLite (WAL), PyJWT, WebSockets
- **Frontend:** React 18, TypeScript, Vite (Tailwind + shadcn/ui arrive with the UI sprints)
- **AI:** provider abstraction with fallback chain — OpenAI → Anthropic → built-in StubProvider (no API keys needed to play or test)

## Quickstart

```bash
# 1. Backend
python -m venv .venv
.venv/Scripts/pip install -e "backend[dev]"     # Windows (Git Bash / PowerShell)
# .venv/bin/pip install -e "backend[dev]"       # Linux / macOS

# 2. Frontend
cd frontend && npm install && cd ..

# 3. Run both
.venv/Scripts/python scripts/dev.py
```

| URL | What |
|-----|------|
| http://127.0.0.1:8000/docs | Swagger UI — try the API |
| http://localhost:5173 | Frontend (scaffolded; full UI in upcoming sprints) |

> If port 5173 is taken, Vite shifts to 5174 — check the dev script's console output. Full command list: [quick-reference.md](quick-reference.md).

No AI API keys are required: without keys the game runs on the built-in StubProvider. To use real models, set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `backend/.env`. Other settings: `DATABASE_URL`, `JWT_SECRET_KEY`, `STUB_PROVIDER_ONLY=true`.

## Tests

```bash
cd backend && ../.venv/Scripts/python -m pytest -v --cov=app
cd frontend && npm run test        # from the UI sprints onward
```

## Project layout

```
backend/app/
  api/v1/            REST routers (auth, challenges, session)
  core/              config, security (JWT/PBKDF2), exceptions, in-process state
  db/                SQLModel models, async SQLite connection, Alembic migrations
  data/              challenge_library/ (25 JSON) · stub_entries/ (25 pools) · ai_prompts/
  repositories/      data access layer
  services/          challenge engine, constraint engine, scoring
docs/                architecture, implementation guide, sprint plan, game design, challenge library
scripts/dev.py       one-command local dev (backend :8000 + frontend :5173)
worklog.md           sprint-by-sprint build journal
```

## Design principles

- **The AI gets the same prompt as the human.** No hidden instructions, ever — the AI prompt is a deterministic transformation of the challenge definition and fully auditable.
- **Time asymmetry is the game.** The AI has unlimited time; you have 15–60 seconds. That's the whole tension.
- **Challenges are data, not code.** Every challenge lives as JSON; adding one requires zero code changes.
- **No raw prompt leakage.** AI responses are sanitized before they reach the UI.
- **Business logic lives in the backend.** The frontend is a thin presentation layer.
