# Database Schema

Normalized relational schema. SQLite is the default for local development;
PostgreSQL is supported via `DATABASE_URL` (untested here — see README and
`docs/deployment.md`). UUIDs for entity identifiers, `created_at` / `updated_at`
timestamps, foreign keys, and indexes on hot paths.

## Tables

### `users`
| Column | Type | Notes |
|---|---|---|
| id | uuid (36) | pk |
| email | varchar(320) | unique, indexed |
| password_hash | varchar(512) | argon2 |
| name | varchar(200) | |
| role | varchar(32) | admin/member |

### `clients`
| Column | Type | Notes |
|---|---|---|
| id | uuid | pk |
| name | varchar(200) | indexed |
| company | varchar(200) | |
| status | varchar(32) | active/prospect/inactive/churned, indexed |
| email, phone, address | varchar | |
| payment_terms | varchar(200) | |
| contract_notes, notes | text | |
| created_at, updated_at | datetime | |

### `projects`
| Column | Type | Notes |
|---|---|---|
| id | uuid | pk |
| name | varchar(200) | indexed |
| description | text | |
| client_id | uuid FK → clients | nullable, on delete SET NULL |
| status | varchar(32) | active/on_hold/completed/cancelled, indexed |
| priority | varchar(16) | low/medium/high/critical |
| start_date, deadline | date | deadline indexed |
| progress | numeric(5,2) | 0–100 |
| notes | text | |

### `project_milestones`
`id`, `project_id` (FK, cascade), `title`, `due_date`, `status` (todo/done).

### `tasks`
`id`, `title` (indexed), `description`, `priority` (indexed), `status` (indexed),
`project_id` (FK, nullable), `client_id` (FK, nullable), `start_date`, `due_date` (indexed),
`completed_at`, `recurrence`.
Indexes on `(status, due_date)` and `client_id`.

### `task_dependencies`
`id`, `task_id` (FK), `depends_on_id` (FK), `created_at`, unique constraint
(`task_id`, `depends_on_id`).

### `meetings`
`id`, `title`, `client_id`, `project_id`, `scheduled_at`, `summary`, `outcome`.

### `knowledge_documents` / `knowledge_sources` / `daily_notes`
DB mirrors of vault metadata (path, title, folder, frontmatter, tags). Content
authoritative in the vault. `knowledge_documents` / `daily_notes` /
`knowledge_sources` are additive mirrors; the vault remains authoritative for content.

### `content_items`
`id`, `title` (indexed), `platform`, `format`, `status` (indexed), `body`,
`scheduled_for`, `published_url`, `performance` (JSON), `tags` (JSON), `notes`.

### `financial_transactions`
`id`, `kind` (income/expense, indexed), `amount` (numeric(14,2)), `currency`
(default USD), `category`, `client_id`, `project_id`, `invoice_id`, `date` (indexed),
`description`. Index on (`date`, `kind`).

### `invoices`
`id`, `number` (unique, indexed), `client_id`, `amount` (numeric(14,2)), `currency`,
`due_date` (indexed), `status` (indexed: draft/sent/paid/overdue/void), `paid_date`, `description`.

### `research_documents`
`id`, `title` (indexed), `source_urls` (JSON list), `summary`, `tags` (JSON list),
`related_projects` (JSON list), `created_from` (manual/ai/import).

### `business_reports`
`id`, `type` (indexed), `title`, `body` (Markdown), `source` (JSON), `agent`.

### `ai_executions`
`id`, `agent` (indexed), `status` (indexed: pending/success/failed/awaiting_approval),
`input` (JSON), `output` (text), `provider`, `model`, `tokens_in`, `tokens_out`,
`duration_ms`, `error`.

### `approval_requests`
`id`, `type` (indexed), `payload` (JSON), `status` (indexed), `reason`.

### `automation_workflows` / `automation_executions`
Workflows: `id`, `name` (unique), `description`, `status`, `schedule`.
Executions: `id`, `workflow_id` (FK, cascade), `status` (indexed), `payload`,
`result` (JSON), `error`, `idem_key` (unique), `started_at`, `finished_at`.

### `queue_requests`
`id`, `type` (indexed), `description`, `input` (JSON), `priority`, `status` (indexed:
pending/validating/processing/awaiting_approval/completed/failed/cancelled/requires_review),
`error`, `result` (JSON).

### `activity_logs`
`id`, `actor`, `action`, `entity_type`, `entity_id`, `summary`, `created_at` (indexed).

## Indexes

- `users.email` (unique)
- `clients.status`, `projects.status`, `projects.deadline`, `projects.client_id`
- `tasks.title`, `tasks.priority`, `tasks.status`, `tasks.project_id`, `tasks.client_id`, `tasks.due_date`
- `task_dependencies.task_id`, `task_dependencies.depends_on_id`
- `invoices.status`, `invoices.due_date`, `invoices.client_id`
- `financial_transactions.date`, `financial_transactions.kind`, `financial_transactions.client_id`
- `ai_executions.agent`, `ai_executions.status`
- `approval_requests.type`, `approval_requests.status`
- `automation_executions.workflow_id`, `automation_executions.status`
- `queue_requests.type`, `queue_requests.status`
- `activity_logs.created_at`
- Composite: `tasks(status, due_date)`, `invoices(status, due_date)`, `transactions(date, kind)`

## Migrations

`alembic upgrade head` applies the initial schema (22 tables). Migrations are
auto-generated and committed in `apps/api/alembic/versions/`.
