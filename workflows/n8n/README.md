# n8n Workflow Templates

These templates are **starting points for n8n** — not fake automations. Each
workflow imports into n8n and must be adapted to your own credentials, webhook
secrets, and notification channel before relying on it. The Business OS talks to
n8n over webhooks (`POST {N8N_WEBHOOK_BASE_URL}/{workflow-name}`) and records
executions in its own database.

## Workflows

| Template | Trigger | Description |
|---|---|---|
| `daily-brief.json` | Schedule `0 6 * * *` | Daily business brief from projects, tasks, invoices and AI agents |
| `pre-meeting-brief.json` | Manual / webhook | Meeting-prep brief for a client or project |
| `content-draft.json` | File watcher on `08-QUEUE/` + webhook | Generate a draft from a queued request, await human review |
| `weekly-content-performance.json` | Schedule `0 9 * * 1` | Monday content-performance report |
| `financial-updates.json` | Webhook (on new transaction/invoice) | Validate, update, and remind about invoices |
| `weekly-review.json` | Schedule `0 20 * * 0` | Sunday weekly progress review |
| `quarterly-review.json` | Schedule first-of-quarter | Quarterly strategic retrospective |

## Importing into n8n

1. Start n8n (`docker compose up n8n` in an n8n deployment, or `npx n8n start`).
2. In n8n: `Workflows → Import from file` and pick the JSON.
3. Fill in credentials (email, Telegram, Slack, or HTTP webhook secrets).
4. Point the webhook trigger URL at your Business OS webhook endpoint:

   ```
   https://<your-domain>/api/...   # or the original /api/automation/workflows/<name>/trigger
   ```

5. Test with `▶ Execute workflow` once, then activate.

## What is and is not automated here

- **In this app:** webhook triggers and execution tracking (honest, real).
- **In n8n:** scheduling, notifications, retries, multi-step orchestration.
- Not implemented in this app: a background scheduler inside FastAPI. Scheduling
  belongs to n8n (or cron). Keeping it external avoids duplicating n8n.
