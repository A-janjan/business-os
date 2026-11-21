# Automation: n8n Integration

Business OS does not reimplement n8n. It triggers workflows over webhooks and
tracks executions in its own database. n8n is the external engine for
scheduling, retries, notifications, and multi-step orchestration.

## Workflow registry

Seven workflow definitions are registered in `app/automation/n8n.py`:

| Workflow | Trigger | Cadence |
|---|---|---|
| daily-brief | schedule | `0 6 * * *` |
| pre-meeting-brief | manual/webhook | on meeting |
| content-draft | file-watcher on `08-QUEUE/` | event |
| weekly-content-performance | schedule | `0 9 * * 1` |
| financial-updates | event | on new transaction/invoice |
| weekly-review | schedule | `0 20 * * 0` |
| quarterly-review | schedule | first-of-quarter |

## Triggering a workflow

```bash
curl -X POST http://127.0.0.1:8000/api/automation/workflows/weekly-review/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payload": {}}'
```

The API creates an `automation_executions` row (`status=queued`), then either
- POSTs `{N8N_WEBHOOK_BASE_URL}/{workflow-name}` with
  `{workflow, execution_id, idempotency_key, payload}`, or
- marks the execution `failed` with an explicit error if n8n is not configured.

**n8n is not configured → n8n triggers always record honest failures, never
fake successes.** This is by design: no fake automation.

## Idempotency

Each trigger carries an `idempotency_key` (auto-generated UUID or
`idempotency_key` in the payload). Duplicate triggers with the same key return
the existing execution instead of firing again. The queue has its own lifecycle
protection (`pending|failed|requires_review` → process; others are rejected).

## Execution tracking

`GET /api/automation/executions` lists history (status, payload, result, error,
timestamps). The frontend's Automations page renders the workflow templates and
execution history side by side.

## n8n workflow templates

Templates live in `workflows/n8n/*.json`. The `daily-brief.json` template shows a
full pattern (Schedule → fetch summary → generate brief → notify). Other
templates are documented skeletons — import, adapt credentials and webhook
secrets, and test before relying on them.

## What is intentionally NOT in the app

- **In-process schedulers** (no APScheduler, no celery beat) — scheduling belongs
  to n8n (or cron).
- **In-process retry loops** — n8n handles retries; the app records execution.
- **Real-time callbacks** — n8n is asynchronous; the app does not poll it.
