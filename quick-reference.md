# Man vs. Machine — Quick Reference

> Everyday commands. Local-first setup: **no Docker** — FastAPI + SQLite backend, Vite frontend.
> Full details: `AGENTS.md` (rules), `docs/03_Sprint_Plan.md` (sprints), `worklog.md` (journal).

---

## One-time setup

```bash
# Backend (Python 3.11+; project venv at .venv/)
python -m venv .venv
.venv/Scripts/pip install -e "backend[dev]"      # Git Bash / PowerShell on Windows
# (Linux/macOS: .venv/bin/pip install -e "backend[dev]")

# Frontend (Node 18+)
cd frontend && npm install
```

## Run (daily dev)

```bash
# Both servers, one command (from project root)
.venv/Scripts/python scripts/dev.py

# Or individually
cd backend  && ../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

| URL | What |
|-----|------|
| http://127.0.0.1:8000 | Backend health check (`{"status":"ok"}`) |
| http://127.0.0.1:8000/docs | Swagger UI (interactive API docs) |
| http://localhost:5173 | Frontend (Vite) |

> **Port note:** if your "FLOOD" app is running, it owns 5173 and Vite auto-increments to **5174** —
> check the `scripts/dev.py` console output for the actual URL. Backend CORS already allows 5173–5175.

## Tests

```bash
# Backend (from backend/)
../.venv/Scripts/python -m pytest -v                    # all tests
../.venv/Scripts/python -m pytest -v --cov=app          # with coverage (target >= 80% new code)
../.venv/Scripts/python -m pytest tests/test_e2e.py -v  # E2E, from Sprint 24 (StubProvider, no API keys)

# Frontend (from frontend/) — Vitest, from Sprint 15
npm run test         # or: npx vitest run
```

## Lint & type checks

```bash
# Backend (from backend/)
../.venv/Scripts/python -m ruff check app/ ../scripts
../.venv/Scripts/python -m mypy app/

# Frontend (from frontend/)
npx tsc --noEmit
npx eslint src/        # ESLint config arrives in Sprint 15
```

## Database (SQLite)

- **File:** `backend/manvsmachine.db` (gitignored; auto-created/migrated on backend startup)
- **Driver:** `sqlite+aiosqlite`, WAL mode, `PRAGMA foreign_keys=ON` (enforced per connection in `app/db/connection.py`)
- **Migrations:** Alembic — run from `backend/` with the venv's Python

```bash
cd backend
../.venv/Scripts/python -m alembic upgrade head                        # apply all migrations
../.venv/Scripts/python -m alembic revision --autogenerate -m "..."    # new migration from model changes
../.venv/Scripts/python -m alembic downgrade -1                        # roll back one
../.venv/Scripts/python -m alembic history                             # list migrations
```

```bash
# Inspect the DB
sqlite3 backend/manvsmachine.db ".tables"
sqlite3 backend/manvsmachine.db "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';"
sqlite3 backend/manvsmachine.db "SELECT * FROM users;"
```

## Sprint loop (per AGENTS.md v1.2)

**plan → scope (worklog entry, in-progress) → implement (TDD: red → green) → verify (pytest + ruff + mypy/tsc + acceptance criteria) → commit (`Sprint N: ...`) + push → close worklog entry**

```bash
git add <files> && git commit -m "Sprint N: summary" && git push origin main
```

- Create/modify **only** the sprint's listed files; anything extra gets flagged in the worklog notes.
- Never break: AI fairness (same prompt as human), time asymmetry (AI unlimited, human 15–60s),
  challenges-as-JSON (no hardcoded logic), business logic in backend services.

## Docs map

| Doc | Purpose |
|-----|---------|
| `docs/01_Master_Architecture.md` | Source of truth — read first |
| `docs/02_Implementation_Guide.md` | Schemas, APIs, services, providers |
| `docs/03_Sprint_Plan.md` | Sprint-by-sprint build guide + changelog |
| `docs/04_Game_Design_Document.md` | Gameplay experience |
| `docs/05_Micro_Challenge_Library.md` | The 25 challenge definitions |
| `worklog.md` | Build journal (newest first) |
