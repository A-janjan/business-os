"""n8n integration: webhook triggers + execution tracking.

n8n is external (not reimplemented). This module:
- triggers workflows via webhooks (workflow definitions live in workflows/n8n/),
- tracks executions in the database,
- and is honest about the fact that in-app execution does not replaces n8n's
  scheduler: scheduling itself is n8n's job; this app triggers and records.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AutomationExecution, AutomationWorkflow

WORKFLOWS = {
    "daily-brief": {
        "description": "Every day 06:00 — daily business brief from active projects, tasks, deadlines.",
        "schedule": "0 6 * * *",
    },
    "pre-meeting-brief": {
        "description": "On scheduled meeting or manual request — pre-meeting brief for client/project.",
        "schedule": "manual",
    },
    "content-draft": {
        "description": "On new file in 08-QUEUE/ — generate a draft from the request, await human review.",
        "schedule": "file-watcher",
    },
    "weekly-content-performance": {
        "description": "Every Monday — content performance report.",
        "schedule": "0 9 * * 1",
    },
    "financial-updates": {
        "description": "On new financial entry / invoice due — validate, update, reminders.",
        "schedule": "event-driven",
    },
    "weekly-review": {
        "description": "Every Sunday 20:00 — weekly progress review from daily notes and activity.",
        "schedule": "0 20 * * 0",
    },
    "quarterly-review": {
        "description": "First day of each quarter — quarterly strategic review.",
        "schedule": "first-of-quarter",
    },
}


def seed_workflows(db: Session) -> None:
    for name, spec in WORKFLOWS.items():
        existing = db.scalars(select(AutomationWorkflow).where(AutomationWorkflow.name == name)).first()
        if existing is None:
            db.add(AutomationWorkflow(name=name, description=spec["description"], schedule=spec["schedule"], status="disabled"))
    db.commit()


def list_workflows(db: Session) -> list[AutomationWorkflow]:
    return list(db.scalars(select(AutomationWorkflow).order_by(AutomationWorkflow.name)))


async def trigger_workflow(db: Session, workflow_name: str, payload: dict, idempotency_key: str | None = None) -> AutomationExecution:
    """Trigger an n8n workflow and record it.

    Returns the execution row. If n8n is not configured, returns an execution
    marked 'failed' with an explicit message — never a fake success.
    """
    workflow = db.scalars(select(AutomationWorkflow).where(AutomationWorkflow.name == workflow_name)).first()
    if workflow is None:
        raise ValueError(f"unknown workflow: {workflow_name}")

    idem_key = idempotency_key or str(uuid.uuid4())
    existing = db.scalars(select(AutomationExecution).where(AutomationExecution.idem_key == idem_key)).first()
    if existing is not None:
        return existing  # idempotent

    execution = AutomationExecution(
        workflow_id=workflow.id,
        status="queued",
        payload=payload or {},
        idem_key=idem_key,
        started_at=None,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    settings = get_settings()

    if not settings.n8n_enabled or not settings.n8n_webhook_base_url:
        execution.status = "failed"
        execution.error = "n8n is not configured (N8N_ENABLED=false or N8N_WEBHOOK_BASE_URL missing). See workflows/n8n/ for setup."
        execution.finished_at = _utcnow()
        db.commit()
        db.refresh(execution)
        return execution

    execution.status = "running"
    execution.started_at = _utcnow()
    db.commit()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.n8n_webhook_base_url.rstrip('/')}/{workflow_name}",
                json={"workflow": workflow_name, "execution_id": execution.id, "idempotency_key": idem_key, "payload": payload or {}},
                headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {settings.n8n_api_key}"} if settings.n8n_api_key else {})},
            )
            resp.raise_for_status()
        execution.status = "success"
        execution.result = {"status_code": resp.status_code, "triggered_via": "webhook"}
    except Exception as exc:  # noqa: BLE001
        execution.status = "failed"
        execution.error = str(exc)

    execution.finished_at = _utcnow()
    db.commit()
    db.refresh(execution)
    return execution


def list_executions(db: Session, limit: int = 50) -> list[AutomationExecution]:
    return list(db.scalars(select(AutomationExecution).order_by(AutomationExecution.created_at.desc()).limit(limit)))
