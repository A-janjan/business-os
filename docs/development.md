# Development Guide

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + JWT + argon2 |
| Frontend | React 18 + TypeScript + Vite |
| Database | SQLite (dev) / PostgreSQL (prod, via `DATABASE_URL`) |
| AI | OpenAI-compatible chat completions (any provider, via `AI_BASE_URL`) |
| Automation | n8n webhooks (external) |

## Prerequisites

- Python 3.11+
- Node 20+

## Setup

```bash
cp .env.example .env       # fill in AI + n8n when ready
make install               # pip + npm
make seed                  # create the knowledge vault structure
make migrate               # create/upgrade DB schema
```

## Run

```bash
make api        # FastAPI on 0.0.0.0:8000 (terminal 1)
make web        # Vite dev server on 0.0.0.0:5173 (terminal 2)
```

The Vite dev server proxies `/api/*` to the backend, so the browser never needs
to know the API address. Hot reload works on both sides.

## Tests

```bash
make test         # everything
make test-api     # pytest (backend)
make test-web     # vitest (frontend)
```

Backend: unit + API integration tests (`apps/api/tests/`). They use an isolated
SQLite database, temp vault, and an isolated test client — no real credentials.
AI features are tested with a scripted fake provider, never a real network call.

Frontend: tests for formatters, the API client, and rendering components.

## Code quality

- Backend: Ruff (config in `apps/api/pyproject.toml`).
- Frontend: TypeScript strict, ESLint-style via vite/tsc. Run `npm run build`
  (tsc + vite) as a gate before merging.

## Linting and type checks

```bash
cd apps/api && ruff check .
cd apps/web && npx tsc -b && npm run build
```

## Resetting state

- SQLite DB: `rm data/business_os.db` then `make migrate`.
- Vault: `rm -rf knowledge/*` then `make seed`. **Do not do this in production
  if you have real notes** — the vault is your business memory.

## CI shape (not yet wired)

A GitHub Actions pipeline would run: (1) frontend typecheck + tests + build,
(2) backend tests, (3) lint. See `docs/contributing.md`.
