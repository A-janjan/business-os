# Implementation Roadmap

Phases, gates, and status. Dates are illustrative; the project is intentionally
phased so partial work can ship honestly.

## Phase 0 — Repository inspection
✅ Done — empty workspace, all green sequences wired.

## Phase 1 — Foundation
✅ Done — project structure, FastAPI backend, React SPA, SQLite/Alembic, Docker
compose, configuration management, logging, health checks, bootstrap admin + JWT.

## Phase 2 — Knowledge infrastructure
✅ Done — Markdown repository, vault structure, frontmatter handling,
create/read/update/search/archive, backlinks, daily-note extraction, Obsidian compatibility.

## Phase 3 — Core business modules
✅ Done — Clients, Projects (+milestones), Tasks (+dependencies), Daily Notes,
Content, Finance (transactions + invoices + summaries), Research, Reports.

## Phase 4 — AI infrastructure
✅ Done — LLM provider abstraction, agent registry/executor, context retrieval,
structured output validation, AI execution logs, approval manager.

Tables, schemas, and routes are committed; the executor is fully working and
tested — including with a scripted fake provider. With no provider configured,
AI features return an explicit 503.

## Phase 5 — Specialized agents
✅ Done — Business Analyst, Project Manager, Client Intelligence, Content
(approval-gated), Financial Analyst, Research, Executive Assistant. All
registered and executable through the same executor.

## Phase 6 — Automation integration
✅ Done — n8n webhook triggers with execution tracking + idempotency,
workflow templates + README. In-app scheduling is deliberately **not**
implemented (n8n owns it). Queue lifecycle is implemented as a synchronous,
status-tracked in-app process.

## Phase 7 — Reporting and intelligence
✅ Done — deterministic weekly review (no AI), AI daily brief (when configured),
reports list + viewer, AI activity panel in the dashboard.

## Phase 8 — Hardening & deployment
🟡 Partial — Docker compose files written (untested: Docker unavailable),
CI not wired, Postgres untested, backup/restore documented but not rehearsed.

## What remains (planned)

- Scheduled in-process queue worker — **planned**, deferred to n8n.
- n8n-side scheduling of the seven templates — **planned** (requires n8n instance).
- SQLite → PostgreSQL verification — **planned** (requires Docker/Postgres).
- Frontend test coverage for full pages (currently unit-level) — **planned**.
- CI pipeline (GitHub Actions) — **planned**.
- Backups/restore drill — **planned**.
