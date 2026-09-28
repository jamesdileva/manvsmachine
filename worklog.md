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
