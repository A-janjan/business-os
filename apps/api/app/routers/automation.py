"""Automation routes (n8n triggers + execution tracking)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..automation.n8n import WORKFLOWS, list_workflows, list_executions, trigger_workflow
from ..database import get_db
from ..deps import get_current_user, log_activity
from ..models import AutomationExecution, AutomationWorkflow, User

router = APIRouter(prefix="/automation", tags=["automation"])


def _workflow_dict(w: AutomationWorkflow) -> dict:
    return {
        "id": w.id, "name": w.name, "description": w.description,
        "schedule": w.schedule, "status": w.status,
        "created_at": w.created_at.isoformat(), "updated_at": w.updated_at.isoformat(),
    }


def _exec_dict(e: AutomationExecution) -> dict:
    return {
        "id": e.id, "workflow_id": e.workflow_id, "status": e.status,
        "payload": e.payload or {}, "result": e.result or {},
        "error": e.error, "idem_key": e.idem_key,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "finished_at": e.finished_at.isoformat() if e.finished_at else None,
        "created_at": e.created_at.isoformat(),
    }


@router.get("/workflows")
def get_workflows(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = list_workflows(db)
    known = {w.name for w in items}
    for name in WORKFLOWS:
        if name not in known:
            items.append(AutomationWorkflow(name=name, description=WORKFLOWS[name]["description"],
                                            schedule=WORKFLOWS[name]["schedule"], status="disabled"))
    return {"items": [_workflow_dict(w) for w in items]}


@router.post("/workflows/{name}/trigger", status_code=202)
async def trigger(name: str, payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if name not in WORKFLOWS:
        raise HTTPException(status_code=404, detail="unknown workflow")
    idem = payload.get("idempotency_key")
    try:
        execution = await trigger_workflow(db, name, payload.get("payload", {}), idempotency_key=idem)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
    log_activity(db, "system", "workflow.triggered", "automation_execution", execution.id, f"Workflow {name} triggered")
    db.commit()
    return _exec_dict(execution)


@router.get("/executions")
def get_executions(limit: int = 50, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = list_executions(db, limit=limit)
    return {"items": [_exec_dict(e) for e in items], "total": len(items)}


@router.get("/executions/{execution_id}")
def get_execution(execution_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    e = db.get(AutomationExecution, execution_id)
    if e is None:
        raise HTTPException(status_code=404, detail="execution not found")
    return _exec_dict(e)
