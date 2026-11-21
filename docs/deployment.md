# Deployment

## Prerequisites

- Docker + Docker Compose (for the reference deployment)
- A PostgreSQL database (either the compose service or an external one)
- An OpenAI-compatible LLM provider (optional but recommended)
- n8n instance (optional, only for automated workflows)

## Docker deployment

```bash
cp .env.example .env
# Set AUTH_SECRET, POSTGRES_PASSWORD, DATABASE_URL if using external Postgres,
# AI_BASE_URL/AI_API_KEY/AI_MODEL for AI features,
# N8N_* for automation.
docker compose up --build -d
```

Services:

- `db` — PostgreSQL 16 (persistent volume)
- `api` — FastAPI on `:8000` (`/api/docs` for Swagger)
- `web` — nginx serving the React SPA on `:5173`→`:80` with `/api` proxied to `api:8000`

The API container runs `uvicorn` with the app's `lifespan`, which creates all
tables on first start and seeds the workflow registry.

**Note:** the compose stack has not been run in this sandbox (Docker is
unavailable here). The components are straightforward and the API's
filesystem/DB defaults are SQLite for dev — treat the Postgres path as
"supported, verify before relying on it in production".

## No-Docker deployment

```bash
# 1. Install
pip install -r apps/api/requirements.txt alembic
cd apps/web && npm install

# 2. Configure
cp .env.example .env
# set DATABASE_URL=postgresql+psycopg://..., AUTH_SECRET (strong), AI_*

# 3. Migrate
cd apps/api && alembic upgrade head

# 4. Run API behind a reverse proxy (e.g. nginx/traefik)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. Serve the frontend build
cd apps/web && npm run build
# serve apps/web/dist behind the same reverse proxy path or a CDN
```

Set `ENV=production`, a strong `AUTH_SECRET`, explicit `CORS_ORIGINS`, and
restrict `ADMIN_BOOTSTRAP` to `false`.

## Backups

- **Database:** `pg_dump` or file-level snapshot of the SQLite file.
- **Vault:** the vault is plain Markdown — `rsync`, `git`, or `tar` it.
- **Env:** never commit `.env`; keep a copy of the production secrets with your
  team/password manager, plus an offline copy.

## Disaster recovery

1. Restore the database (`psql` or copy the SQLite file).
2. Restore the vault (`rsync knowledge/`).
3. Re-run the API; tables and the workflow registry are created automatically
   on start.
