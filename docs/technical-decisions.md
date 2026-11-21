# Technical Decisions

## ADR-001 — Modular monolith, not microservices
**Decision:** Single FastAPI app + Vite SPA + SQLite/Postgres.
**Why:** A personal business OS does not need microservice overhead. One
deployable API keeps debugging, auth, transactions, and tests simple.
**Boundary:** Domain logic lives in `app/`; routes are thin.

## ADR-002 — SQLite for dev, PostgreSQL for prod
**Decision:** Default `DATABASE_URL` is SQLite; SQLAlchemy is configured so
PostgreSQL works with one env change. Docker Compose sets up Postgres.
**Why:** Zero-setup local development; production-grade option documented.
**Status:** SQLite verified in tests; Postgres path untested in this sandbox.

## ADR-003 — Vault as source of truth, DB mirrors metadata
**Decision:** Long-form content lives in Markdown; DB holds lightweight mirrors
(`knowledge_documents`, `daily_notes`, `knowledge_sources`).
**Why:** Files are human-editable, portable, and Obsidian-compatible. DB is
kept lean and never authoritative for textual content.

## ADR-004 — Markdown parsing is stdlib + PyYAML
**Decision:** Custom frontmatter parser (`yaml.safe_load`), no Obsidian plugin.
**Why:** The app must work with a plain Markdown directory, not proprietary
Obsidian APIs.

## ADR-005 — No fake AI outputs
**Decision:** With no provider configured, every AI endpoint returns an explicit
503. No fake "success" strings, no canned drafts.
**Why:** Honest failure over plausible-but-fake AI.

## ADR-006 — Approval gate for consequential AI actions
**Decision:** Content-producing agents return `awaiting_approval`; the draft is
saved only after human approval.
**Why:** AI content must not silently land in the business record.

## ADR-007 — No in-process scheduler; n8n is external
**Decision:** Scheduling belongs to n8n or cron. The app triggers webhooks and
tracks executions; it does not run a background scheduler.
**Why:** Duplicating n8n's job inside the app would be a maintenance liability.

## ADR-008 — No `packages/` monorepo split
**Decision:** Flat `app/` package under `apps/api/`.
**Why:** The spec suggested `packages/shared` etc.; that split would add cross-package
builds without a real benefit at this scale. The modular structure is preserved
via `app/knowledge`, `app/ai`, `app/automation`, `app/routers`.

## ADR-009 — Synchronous queue execution (not celery/RQ)
**Decision:** Queue processing runs inside the request cycle with explicit
status transitions.
**Why:** A personal OS does not need a background worker; n8n is the async engine.

## ADR-010 — Soft deletes only
**Decision:** `archived` / `churned` / `void` status transitions, never hard deletes.
**Why:** Business records are durable and auditable.

## ADR-011 — No XSS surface in the frontend
**Decision:** Markdown rendered as plain text; React auto-escapes.
**Why:** Notes are untrusted content.
