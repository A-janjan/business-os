# Business OS

An AI-powered personal business operating system — one place for knowledge, clients,
projects, tasks, daily notes, content, finance, research, and the specialized agents that
help you see your business clearly.

**Capture → Organize → Understand → Decide → Execute → Evaluate → Improve**

- **Knowledge layer:** Markdown vault (Obsidian-compatible). Files are the source of truth — open the vault in Obsidian, any text editor, or `git`, at any time.
- **Business modules:** Clients, Projects, Tasks, Content, Finance, Daily Notes, Research, Reports — all in one web app.
- **AI layer:** seven specialized agents behind one provider-agnostic executor. With no provider configured, every AI feature fails loudly and honestly — it never fabricates output.
- **Automation:** n8n-ready with webhook triggers and execution tracking; you keep n8n as the external engine (it is deliberately not reimplemented).
- **Human control:** content drafts and irreversible actions are approval-gated; nothing publishes or sends without you.

## Quick start

Prerequisites: Python 3.11+ and Node 20+.

```bash
# 1. Install dependencies
make install
# (or: pip install -r apps/api/requirements.txt && cd apps/web && npm install)

# 2. Seed the vault
make seed

# 3. Run the API (terminal 1) and the frontend (terminal 2)
make api        # FastAPI on http://127.0.0.1:8000
make web        # Vite dev server on http://127.0.0.1:5173
```

Open http://localhost:5173, register the first account (this becomes the admin), and start entering clients,
projects, tasks, and notes. The database initializes automatically on first run; `make migrate` applies
Alembic migrations explicitly if you prefer.

Open the API docs at http://127.0.0.1:8000/api/docs (Swagger).

## Feature status (honest)

| Area | Status |
|---|---|
| Foundation (FastAPI + React SPA + SQLite + Alembic) | Implemented |
| Authentication (bootstrap admin, JWT, argon2) | Implemented |
| Knowledge base (Markdown vault, search, backlinks, archive, daily-note extraction) | Implemented |
| Clients, Projects (+milestones), Tasks (+dependencies), Daily Notes, Content, Finance (transactions + invoices + summaries), Research | Implemented |
| Dashboard + Reports (deterministic weekly review; AI daily brief when configured) | Implemented |
| AI orchestration (provider abstraction, agent registry, executor, structured validation, approvals, execution log) | Implemented |
| AI specialization (7 agents defined and executable via the executor) | Implemented |
| n8n automation (webhook triggers, execution tracking, workflow templates) | Implemented (manual triggers; scheduled runs live in n8n) |
| n8n scheduling / queue worker in-process | Planned — scheduled runs are n8n's job |
| PostgreSQL for production | Supported in configuration (untested here — Docker is unavailable in this environment) |

## Repository layout

```
business-os/
├── apps/
│   ├── api/            FastAPI backend (SQLite default, PostgreSQL-ready)
│   │   ├── app/        config, models, routers, knowledge, ai, automation
│   │   ├── alembic/    migrations
│   │   └── tests/      pytest suite (29 tests)
│   └── web/            React + TypeScript SPA (Vite)
├── knowledge/          Obsidian-compatible vault (Markdown + YAML frontmatter)
├── workflows/n8n/      n8n workflow templates + setup notes
├── infrastructure/docker/   production Dockerfiles + nginx
├── infrastructure/scripts/  vault seed script
├── docs/               architecture, schema, agents, API, ops guides
└── tests/              integration/e2e placeholders
```

## Documentation

- [docs/architecture.md](docs/architecture.md) — system design + Mermaid diagrams
- [docs/database-schema.md](docs/database-schema.md) — normalized schema
- [docs/agents.md](docs/agents.md) — agent responsibilities + orchestrator
- [docs/knowledge-management.md](docs/knowledge-management.md) — vault, frontmatter, extraction
- [docs/automation.md](docs/automation.md) — n8n integration
- [docs/api.md](docs/api.md) — full API surface
- [docs/security.md](docs/security.md) — auth, AI safety, data protection
- [docs/development.md](docs/development.md) — local dev, tests, linting
- [docs/deployment.md](docs/deployment.md) — Docker / PostgreSQL deployment
- [docs/implementation-roadmap.md](docs/implementation-roadmap.md) — phases + status
- [docs/agent-status.md](docs/agent-status.md) — multi-agent engineering organization

## What this is not

This is a personal business OS, not a multi-tenant SaaS. It is designed for one operator
(or one small team running a personal business). Single-user auth, single-tenant data,
SQLite or one PostgreSQL database, no role explosion.
