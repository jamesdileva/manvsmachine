# Man vs. Machine — Worklog

Build journal for the project. One entry per sprint (or significant change), newest first.

The per-sprint loop is: **plan → scope → implement (TDD) → verify (tests + lint + acceptance criteria) → commit (+ push) → update this worklog.**

Entry template:

```
## [YYYY-MM-DD] Sprint N — Name
- Status: planned / in-progress / done / blocked
- Plan & scope: what this sprint covers (from docs/03_Sprint_Plan.md) + file list
- Implemented: what was actually built
- Verification: test runs + results, lint/typecheck, acceptance criteria checked
- Commits: short sha + subject
- Notes: deviations, flags, decisions
```

---

## [2026-09-28] Sprint 1 — Project Scaffolding
- Status: done
- Plan & scope: local dev setup with no Docker, per `docs/03_Sprint_Plan.md` Sprint 1. FastAPI skeleton with `GET /` health check (TDD), CORS for localhost:5173, catch-all exception handler, pydantic settings (`DATABASE_URL`, AI keys). Vite + React + TS skeleton (6 files). `scripts/dev.py` one-command launcher (backend :8000 + frontend :5173). `pyproject.toml` includes FastAPI, Uvicorn, SQLModel, SQLAlchemy, aiosqlite, pytest, pytest-asyncio, ruff. Out of scope: DB models (Sprint 2), shadcn/Tailwind (Sprint 15), Redis (dropped). Planned files: `scripts/dev.py`, `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/requirements.txt`, `.python-version`, `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/app.tsx`.
- Implemented: FastAPI app (`app/main.py`: health check, CORS, catch-all JSON 500 handler), pydantic settings (`app/core/config.py`: database_url, AI provider keys, `stub_provider_only`, CORS origins), `scripts/dev.py` (starts uvicorn + vite, propagates crashes, clean Ctrl+C shutdown), Vite + React + TS skeleton (strict mode), `.python-version` (3.14), root `.gitignore`.
- Verification: TDD red→green (`tests/test_health.py`: ModuleNotFoundError before implementation, passes after; 1 passed, 95% coverage). `ruff check` clean on `app/` + `scripts/`. `mypy app/` clean (4 files). `npx tsc --noEmit` clean. Full-stack acceptance via `python scripts/dev.py`: `GET /` → `{"status":"ok"}`, `/docs` → 200, frontend serves the app (title "Man vs. Machine"). Servers stopped cleanly, ports freed.
- Commits: `19385d2` Sprint 1: project scaffolding (FastAPI + Vite, local dev script); worklog + changelog in the follow-up commit.
- Notes (flagged additions beyond the sprint file list): `backend/app/core/__init__.py` + `core/config.py` (Sprint 1's settings requirement needs them; Sprint 4 will extend rather than create config.py); `backend/tests/test_health.py` (TDD requirement); root `.gitignore` + committed `frontend/package-lock.json` (standard hygiene). Port note: 5173 is occupied on this machine by the owner's "FLOOD — Research Console" app while it runs, so Vite auto-increments to 5174 — backend CORS therefore allows 5173–5175. Environment: Python 3.14.3, Node 24.14.1. Known noise: StarletteDeprecationWarning from FastAPI's testclient import (third-party, harmless).

## [2026-09-28] Process setup — worklog & per-sprint loop
- Status: done
- Plan & scope: establish the per-sprint workflow (plan → scope → implement → verify → commit + push → worklog) and this journal. Files: `worklog.md`, `AGENTS.md`.
- Implemented: created `worklog.md` with entry template; added commit + worklog steps to the AGENTS.md Sprint Execution Workflow (v1.2).
- Verification: n/a (process change only).
- Commits: (this entry's commit — "Add worklog and per-sprint sprint workflow")
- Notes: remote `origin` (github.com/jamesdileva/manvsmachine, public) already exists and tracks main — no repo creation needed. Next up: Sprint 1 on the owner's go.

## [2026-09-28] Sprint 0 (wrap-up) — Delivery model decision & docs v1.1
- Status: done
- Plan & scope: review all project docs; decide the delivery model (Electron + SQLite vs local web dashboard vs original hosted Docker stack); amend docs to match before any code is written.
- Implemented: owner chose the **local web dashboard** — FastAPI + SQLite (aiosqlite, WAL) + in-process state; no Docker, no Redis. Hosted deployment (PostgreSQL/Redis/Nginx) documented as post-MVP. Amended: `docs/01_Master_Architecture.md` (§2, §3.1, §5, §7–§10, §15, §16, Appendix B, §22 changelog), `docs/02_Implementation_Guide.md` (§1 schema + SQLite notes, §2/§3 URLs, share route), `docs/03_Sprint_Plan.md` (Sprints 1, 2, 4, 14, 24, 27 + changelog), `AGENTS.md` (v1.1: rule 6 local-first, rule 9, dev commands).
- Verification: consistency sweep (grep) — no stale docker/redis/postgres/JSONB/asyncpg/manvs.io references outside intentional post-MVP notes. No code exists yet; test suites begin with Sprint 1.
- Commits: `bfe4ea7` Amend docs for local-first delivery model (SQLite, no Docker/Redis)
- Notes: Electron rejected for now (packaging cost vs zero MVP gameplay benefit; revisit post-MVP for offline/Ollama). Game rules untouched: AI fairness, time asymmetry, challenges-as-data. Product consequence accepted: local-only means personal stats instead of global daily/leaderboards, and humanity scoring is based on the single player's votes.
