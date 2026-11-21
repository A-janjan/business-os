# API Reference

Base URL: `/api`. Interactive docs at `/api/docs` (Swagger). All endpoints except
`/auth/register`, `/auth/login`, `/health` require a Bearer token.
Every response is JSON. Errors use FastAPI's standard `{"detail": "..."}`.

## Auth
| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | Bootstrap-only (first admin). 403 after registration (unless `ADMIN_BOOTSTRAP=true`). |
| POST | `/api/auth/login` | Returns `{access_token}`. |
| GET | `/api/auth/me` | Current user. |

## Dashboard
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/dashboard/summary` | One call for the home view |

## Knowledge
| Method | Path | Notes |
|---|---|---|
| GET | `/api/knowledge/structure` | Folder tree + note counts |
| GET | `/api/knowledge/notes?q=&folder=&tag=` | Search notes (q=text, folder, tag) |
| GET | `/api/knowledge/note?path=` | Read one note (frontmatter + body + links) |
| POST | `/api/knowledge/notes` | Create note (frontmatter + body) |
| PATCH | `/api/knowledge/note` | Update note (frontmatter / body) |
| POST | `/api/knowledge/note/archive` | Move to `10-ARCHIVE/` |
| GET | `/api/knowledge/backlinks?path=` | Which notes link to this note |

## Daily notes
| Method | Path | Notes |
|---|---|---|
| GET | `/api/notes/` | List daily notes |
| GET | `/api/notes/{YYYY-MM-DD}` | Full note + extracted sections + finance lines |
| PUT | `/api/notes/{YYYY-MM-DD}` | Create/update daily note (writes Markdown file) |

## Clients / Projects / Tasks / Content / Finance / Research / Reports / AI / Automation / Queue
| Method | Path | Purpose |
|---|---|---|
| GET, POST, GET, PUT | `/api/clients/…` | Client CRUD (+ revenue) |
| GET, POST, GET, PUT, DELETE | `/api/projects/…` | Project CRUD + milestones |
| GET, POST, GET, PUT, DELETE | `/api/tasks/…` | Tasks + status transitions + dependencies |
| GET, POST, GET, PUT, PATCH, DELETE | `/api/content/…` | Content items + status |
| GET, POST, DELETE | `/api/finance/transactions` | Transactions |
| POST, GET, PUT, DELETE | `/api/finance/invoices` | Invoices (overdue auto-detected) |
| GET | `/api/finance/summary?month=YYYY-MM` | Monthly income/expense/net |
| GET, POST, GET, PUT, DELETE | `/api/research/…` | Research documents |
| GET, POST, GET | `/api/reports/…` | Reports + weekly-review generation |
| POST | `/api/reports/daily-brief` | AI daily brief (503 when AI not configured) |
| GET, POST | `/api/ai/agents/…` | Agent listing + run |
| POST | `/api/ai/ask` | Executive assistant shorthand |
| GET | `/api/ai/executions` | AI execution history |
| GET | `/api/ai/approvals` | Pending approvals |
| POST | `/api/ai/approvals/{id}/resolve` | Approve/reject (side effects for drafts) |
| GET, POST | `/api/automation/workflows/…` | n8n workflow listing + trigger |
| GET | `/api/automation/executions` | Automation execution history |
| GET, POST, POST | `/api/queue/…` | Queue + process + cancel + status lifecycle |

## Health
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness |
| GET | `/api/health/ready` | Readiness (DB check) |

## Examples

```bash
# Bootstrap the admin and log in
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"me@example.com","password":"very-strong-password","name":"Me"}'

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"me@example.com","password":"very-strong-password"}' | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/dashboard/summary
```
