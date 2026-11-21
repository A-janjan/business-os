"""AI routes: agents, executions, approvals."""
from __future__ import annotations

import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.approvals import APPROVAL_TYPES, ApprovalError, create_approval, list_approvals, resolve_approval
from ..ai.agents import AgentExecutor, AgentOutputError, get_agent_spec, list_agents
from ..ai.context import build_context
from ..ai.providers import NotConfiguredError, get_provider
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user, log_activity
from ..models import AIExecution, ApprovalRequest, ContentItem, User

router = APIRouter(prefix="/ai", tags=["ai"])


def _serialize_execution(e: AIExecution) -> dict:
    return {
        "id": e.id, "agent": e.agent, "status": e.status,
        "input": e.input or {}, "output": e.output,
        "provider": e.provider, "model": e.model,
        "tokens_in": e.tokens_in, "tokens_out": e.tokens_out,
        "duration_ms": e.duration_ms, "error": e.error,
        "created_at": e.created_at.isoformat(),
    }


@router.get("/agents")
def get_agents(_: User = Depends(get_current_user)):
    return {"items": list_agents()}


@router.get("/agents/{name}")
def get_agent(name: str, _: User = Depends(get_current_user)):
    spec = get_agent_spec(name)
    if spec is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return {"name": spec.name, "role": spec.role, "description": spec.description,
            "requires_approval": spec.requires_approval}


@router.post("/agents/{name}/run")
async def run_agent(name: str, payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    spec = get_agent_spec(name)
    if spec is None:
        raise HTTPException(status_code=404, detail="agent not found")
    input_data = payload.get("input", {}) if isinstance(payload.get("input", {}), dict) else {}
    question = str(payload.get("question") or payload.get("q") or "")

    provider = get_provider()
    if not provider.is_configured:
        # Honest failure, not a fake response.
        raise HTTPException(
            status_code=503,
            detail="AI provider not configured. Set AI_BASE_URL, AI_API_KEY and AI_MODEL in .env to enable AI features.",
        )

    settings = get_settings()
    context = build_context(
        db,
        project_id=payload.get("project_id"),
        client_id=payload.get("client_id"),
    )
    executor = AgentExecutor(provider, temperature=settings.ai_temperature, max_tokens=settings.ai_max_tokens)

    execution = AIExecution(
        agent=name, status="pending", input={"input": input_data, "question": question},
        provider=provider.name, model=getattr(provider, "model", ""),
    )
    db.add(execution)
    db.flush()

    result = await executor.run(name, input_data, question=question, context=context)
    started = time.time() - (result.duration_ms / 1000)

    execution.status = result.status
    execution.output = result.output
    execution.tokens_in = result.tokens_in
    execution.tokens_out = result.tokens_out
    execution.duration_ms = result.duration_ms
    execution.error = result.error
    execution.provider = getattr(result, "raw", {}).get("provider", provider.name) if hasattr(result, "raw") else provider.name
    execution.model = result.tokens_out_model or execution.model

    # Approval gate: content-producing agents require human review before the draft is saved.
    approval_id = None
    if result.status == "success" and spec.requires_approval:
        try:
            draft = json.loads(result.output) if result.output else {}
            approval = create_approval(db, "content-draft", {
                "title": draft.get("title", ""),
                "body": draft.get("body", ""),
                "platform": draft.get("platform", "linkedin"),
                "rationale": draft.get("rationale", ""),
                "execution_id": execution.id,
            })
            approval_id = approval.id
            execution.status = "awaiting_approval"
        except Exception as exc:  # noqa: BLE001
            execution.error = f"content approval gate failed: {exc}"
            execution.status = "failed"

    log_activity(db, "ai", f"agent.{name}.run", "ai_execution", execution.id,
                 f"{spec.role} ran ({execution.status})")
    db.commit()
    db.refresh(execution)

    return {**_serialize_execution(execution), "approval_id": approval_id}


@router.post("/ask")
async def ask(payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Executive assistant shorthand."""
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    return await _ask(question, db, payload)


async def _ask(question: str, db: Session, payload: dict):
    spec = get_agent_spec("executive-assistant")
    provider = get_provider()
    if not provider.is_configured:
        raise HTTPException(status_code=503, detail="AI provider not configured")
    context = build_context(db, project_id=payload.get("project_id"), client_id=payload.get("client_id"))
    executor = AgentExecutor(provider, temperature=get_settings().ai_temperature, max_tokens=get_settings().ai_max_tokens)
    execution = AIExecution(agent="executive-assistant", status="pending",
                            input={"input": {"question": question}, "question": question},
                            provider=provider.name, model=getattr(provider, "model", ""))
    db.add(execution)
    db.flush()
    result = await executor.run("executive-assistant", {"question": question}, question=question, context=context)
    execution.status = result.status
    execution.output = result.output
    execution.tokens_in = result.tokens_in
    execution.tokens_out = result.tokens_out
    execution.duration_ms = result.duration_ms
    execution.error = result.error
    log_activity(db, "ai", "agent.executive-assistant.ask", "ai_execution", execution.id, "Executive assistant answered")
    db.commit()
    db.refresh(execution)
    return {**_serialize_execution(execution), "approval_id": None}


@router.get("/executions")
def list_executions(
    agent: str = "",
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(AIExecution).order_by(AIExecution.created_at.desc()).limit(100)
    if agent:
        stmt = stmt.where(AIExecution.agent == agent)
    items = [_serialize_execution(e) for e in db.scalars(stmt)]
    return {"items": items, "total": len(items)}


@router.get("/executions/{execution_id}")
def get_execution(execution_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    execution = db.get(AIExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="execution not found")
    return _serialize_execution(execution)


@router.get("/approvals")
def list_my_approvals(status: str = "", db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = list_approvals(db, status or None)
    return {"items": [{
        "id": a.id, "type": a.type, "payload": a.payload or {}, "status": a.status, "reason": a.reason,
        "created_at": a.created_at.isoformat(), "updated_at": a.updated_at.isoformat(),
    } for a in items], "total": len(items)}


@router.post("/approvals/{approval_id}/resolve")
def resolve_my_approval(approval_id: str, payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    decision = str(payload.get("decision", "")).strip().lower()
    reason = str(payload.get("reason", ""))
    try:
        approval = resolve_approval(db, approval_id, decision, reason)
    except ApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    content_id = None
    if decision == "approved" and approval.type == "content-draft":
        # Side effect: persist the draft as a content item for human review.
        payload_data = approval.payload or {}
        if payload_data.get("title"):
            item = ContentItem(
                title=str(payload_data.get("title")),
                platform=str(payload_data.get("platform") or "linkedin"),
                format="post",
                status="draft",
                body=str(payload_data.get("body") or ""),
                notes=str(payload_data.get("rationale") or ""),
                tags=["ai-generated"],
            )
            db.add(item)
            log_activity(db, "user", "content.ai_draft_approved", "content", item.id, f"Draft '{item.title}' approved to save")
            db.commit()
            db.refresh(item)
            content_id = item.id
    return {"id": approval.id, "type": approval.type, "status": approval.status, "reason": approval.reason, "content_id": content_id}
