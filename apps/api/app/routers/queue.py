"""Queue-based execution for user requests.

Lifecycle:
  PENDING -> VALIDATING -> PROCESSING -> awaiting_approval -> COMPLETED | FAILED
  plus CANCELLED / REQUIRES_REVIEW on rejection.

The queue does NOT reimplement automation; it enqueues AI/report work through
the same executor used by the /ai endpoints, and records every state change.
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.agents import AgentExecutor, get_agent_spec
from ..ai.context import build_context
from ..ai.providers import get_provider
from ..ai.approvals import create_approval
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user, log_activity
from ..models import QueueRequest, User, BusinessReport, Task, FinancialTransaction
from ..schemas import QueueIn

router = APIRouter(prefix="/queue", tags=["queue"])

AGENT_BY_TYPE = {
    "content-draft": "content",
    "project-analysis": "project-manager",
    "meeting-prep": "client-intelligence",
    "daily-brief": "executive-assistant",
    "weekly-review": None,  # deterministic, no LLM
}
PROCESSABLE = {"pending", "failed", "requires_review"}
TERMINAL = {"completed", "cancelled"}


def _serialize(q: QueueRequest) -> dict:
    return {
        "id": q.id, "type": q.type, "description": q.description,
        "input": q.input or {}, "priority": q.priority, "status": q.status,
        "error": q.error, "result": q.result or {},
        "created_at": q.created_at.isoformat(), "updated_at": q.updated_at.isoformat(),
    }


@router.get("/")
def list_queue(status: str = "", db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(QueueRequest).order_by(QueueRequest.created_at.desc()).limit(100)
    if status:
        stmt = stmt.where(QueueRequest.status == status)
    items = list(db.scalars(stmt))
    return {"items": [_serialize(q) for q in items], "total": len(items)}


@router.post("/", status_code=201)
def create_request(payload: QueueIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    req = QueueRequest(type=payload.type, description=payload.description,
                       input=payload.input or {}, priority=payload.priority, status="pending")
    db.add(req)
    db.flush()
    log_activity(db, "user", "queue.created", "queue_request", req.id, f"Queued {req.type}: {req.description[:80]}")
    db.commit()
    return _serialize(req)


@router.get("/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    req = db.get(QueueRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="queue request not found")
    return _serialize(req)


@router.post("/{request_id}/process")
async def process(request_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    req = db.get(QueueRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="queue request not found")
    if req.status not in PROCESSABLE:
        raise HTTPException(status_code=400, detail=f"cannot process request in status '{req.status}'")

    req.status = "validating"
    db.commit()

    # validation
    if not req.description.strip():
        req.status = "requires_review"
        req.error = "request needs a description before processing"
        db.commit()
        return _serialize(req)

    req.status = "processing"
    db.commit()

    try:
        if req.type == "weekly-review":
            result = _weekly_review_work(db, req)
            req.status = "completed"
            req.result = result
        else:
            result = await _process_ai(req, db)
            if req.type == "content-draft":
                req.status = "awaiting_approval"
                req.result = result
            else:
                req.status = "completed"
                req.result = result
    except Exception as exc:  # noqa: BLE001
        req.status = "failed"
        req.error = str(exc)
        db.commit()
        log_activity(db, "system", "queue.failed", "queue_request", req.id, f"Queue {req.type} failed: {exc}")
        return _serialize(req)

    db.commit()
    log_activity(db, "system", "queue.processed", "queue_request", req.id, f"Queue {req.type} -> {req.status}")
    db.commit()
    db.refresh(req)
    return _serialize(req)


@router.post("/{request_id}/cancel")
def cancel(request_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    req = db.get(QueueRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="queue request not found")
    if req.status in TERMINAL:
        raise HTTPException(status_code=400, detail=f"cannot cancel request in status '{req.status}'")
    req.status = "cancelled"
    db.commit()
    return _serialize(req)


async def _process_ai(req: QueueRequest, db: Session) -> dict:
    agent_name = AGENT_BY_TYPE.get(req.type)
    if agent_name is None:
        raise ValueError(f"unsupported queue type: {req.type}")
    provider = get_provider()
    if not provider.is_configured:
        raise ValueError("AI provider not configured — set AI_BASE_URL/AI_MODEL in .env")
    spec = get_agent_spec(agent_name)
    if spec is None:
        raise ValueError(f"unknown agent for queue type: {req.type}")

    context = build_context(db, project_id=req.input.get("project_id"), client_id=req.input.get("client_id"))
    executor = AgentExecutor(provider, temperature=get_settings().ai_temperature, max_tokens=get_settings().ai_max_tokens)
    result = await executor.run(agent_name, req.input, question=req.description, context=context)

    if result.status != "success":
        raise ValueError(f"agent execution failed: {result.error}")

    output = json.loads(result.output) if result.output else {}

    if req.type == "content-draft":
        approval = create_approval(db, "content-draft", {
            "title": output.get("title", ""),
            "body": output.get("body", ""),
            "platform": output.get("platform", "linkedin"),
            "rationale": output.get("rationale", ""),
            "queue_request_id": req.id,
        })
        return {"approval_id": approval.id, "title": output.get("title", ""), "status": "awaiting_approval"}

    # persist a business report for the run
    report = BusinessReport(
        type="queue-run",
        title=f"{spec.role} — {req.description[:80]}",
        body=json.dumps(output, indent=2),
        source={"queue_request_id": req.id, "type": req.type, "agent": agent_name},
        agent=agent_name,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"report_id": report.id, "agent": agent_name, "status": "completed"}


def _weekly_review_work(db: Session, req: QueueRequest) -> dict:
    from ..routers.reports import _weekly_review_body
    data = _weekly_review_body(db)
    report = BusinessReport(
        type="weekly-review",
        title=f"Weekly Review — {data['week_start']} → {data['week_end']}",
        body=data["body"],
        source=data,
        agent="system",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"report_id": report.id, "status": "completed", "summary": data}
