"""Tasks CRUD + status transitions + dependencies."""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, log_activity
from ..models import Client, Project, Task, TaskDependency, User
from ..schemas import TaskIn

router = APIRouter(prefix="/tasks", tags=["tasks"])

VALID_STATUSES = {"todo", "in_progress", "blocked", "done", "archived"}


def _serialize(task: Task, db: Session) -> dict:
    proj = db.get(Project, task.project_id) if task.project_id else None
    client = db.get(Client, task.client_id) if task.client_id else None
    return {
        "id": task.id, "title": task.title, "description": task.description,
        "priority": task.priority, "status": task.status,
        "project_id": task.project_id, "project_name": proj.name if proj else None,
        "client_id": task.client_id, "client_name": client.name if client else None,
        "start_date": task.start_date.isoformat() if task.start_date else None,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "recurrence": task.recurrence,
        "created_at": task.created_at.isoformat(), "updated_at": task.updated_at.isoformat(),
    }


def _apply_status(task: Task, new_status: str) -> None:
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"unknown status: {new_status}")
    task.status = new_status
    if new_status == "done" and task.completed_at is None:
        task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if new_status != "done":
        task.completed_at = None


@router.get("/")
def list_tasks(
    status: str = "",
    project_id: str = "",
    client_id: str = "",
    overdue: bool = False,
    due_before: str = "",
    include_done: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Task)
    if status:
        stmt = stmt.where(Task.status == status)
    if project_id:
        stmt = stmt.where(Task.project_id == project_id)
    if client_id:
        stmt = stmt.where(Task.client_id == client_id)
    today = date.today()
    if overdue:
        stmt = stmt.where(Task.status.notin_(["done", "archived"]), Task.due_date < today)
    if due_before:
        try:
            stmt = stmt.where(Task.due_date <= date.fromisoformat(due_before))
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid due_before date")
    if not include_done:
        stmt = stmt.where(Task.status.notin_(["done", "archived"]))
    stmt = stmt.order_by(Task.due_date.nullslast(), Task.created_at.desc()).limit(500)
    items = list(db.scalars(stmt))
    return {"items": [_serialize(t, db) for t in items], "total": len(items)}


@router.post("/", status_code=201)
def create_task(payload: TaskIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    data = payload.model_dump()
    if data.get("project_id") and db.get(Project, data["project_id"]) is None:
        raise HTTPException(status_code=400, detail="project not found")
    if data.get("client_id") and db.get(Client, data["client_id"]) is None:
        raise HTTPException(status_code=400, detail="client not found")
    task = Task(**data)
    _apply_status(task, task.status)
    db.add(task)
    db.flush()
    log_activity(db, "user", "task.created", "task", task.id, f"Task '{task.title}' created")
    db.commit()
    return _serialize(task, db)


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return _serialize(task, db)


@router.put("/{task_id}")
def update_task(task_id: str, payload: TaskIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    data = payload.model_dump()
    if data.get("project_id") and db.get(Project, data["project_id"]) is None:
        raise HTTPException(status_code=400, detail="project not found")
    if data.get("client_id") and db.get(Client, data["client_id"]) is None:
        raise HTTPException(status_code=400, detail="client not found")
    for key, value in data.items():
        setattr(task, key, value)
    _apply_status(task, task.status)
    log_activity(db, "user", "task.updated", "task", task.id, f"Task '{task.title}' updated")
    db.commit()
    return _serialize(task, db)


@router.patch("/{task_id}/status")
def set_status(task_id: str, payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    _apply_status(task, str(payload.get("status", "")))
    log_activity(db, "user", "task.status", "task", task.id, f"'{task.title}' -> {task.status}")
    db.commit()
    return _serialize(task, db)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    task.status = "archived"
    db.commit()


@router.post("/{task_id}/dependencies", status_code=201)
def add_dependency(task_id: str, payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    dep_id = str(payload.get("depends_on_id", ""))
    dep = db.get(Task, dep_id)
    if dep is None:
        raise HTTPException(status_code=404, detail="dependency task not found")
    if dep_id == task_id:
        raise HTTPException(status_code=400, detail="task cannot depend on itself")
    existing = db.scalars(select(TaskDependency).where(TaskDependency.task_id == task_id, TaskDependency.depends_on_id == dep_id)).first()
    if existing:
        return {"id": existing.id, "task_id": task_id, "depends_on_id": dep_id}
    dep = TaskDependency(task_id=task_id, depends_on_id=dep_id)
    db.add(dep)
    db.commit()
    return {"id": dep.id, "task_id": dep.task_id, "depends_on_id": dep.depends_on_id}
