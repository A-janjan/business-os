"""Projects CRUD + milestones."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, log_activity
from ..models import Project, ProjectMilestone, Client, User
from ..schemas import MilestoneIn, ProjectIn

router = APIRouter(prefix="/projects", tags=["projects"])


def _serialize(project: Project, db: Session) -> dict:
    client = db.get(Client, project.client_id) if project.client_id else None
    milestones = list(db.scalars(select(ProjectMilestone).where(ProjectMilestone.project_id == project.id).order_by(ProjectMilestone.created_at)))
    return {
        "id": project.id, "name": project.name, "description": project.description,
        "client_id": project.client_id,
        "client_name": client.name if client else None,
        "status": project.status, "priority": project.priority,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "deadline": project.deadline.isoformat() if project.deadline else None,
        "progress": float(project.progress or 0),
        "notes": project.notes,
        "created_at": project.created_at.isoformat(), "updated_at": project.updated_at.isoformat(),
        "milestones": [{
            "id": m.id, "project_id": m.project_id, "title": m.title,
            "due_date": m.due_date.isoformat() if m.due_date else None, "status": m.status,
        } for m in milestones],
    }


@router.get("/")
def list_projects(status: str = "", db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(Project).order_by(Project.updated_at.desc())
    if status:
        stmt = stmt.where(Project.status == status)
    return {"items": [_serialize(p, db) for p in db.scalars(stmt)]}


@router.post("/", status_code=201)
def create_project(payload: ProjectIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = payload.model_dump()
    if data.get("client_id") and db.get(Client, data["client_id"]) is None:
        raise HTTPException(status_code=400, detail="client not found")
    project = Project(**data)
    db.add(project)
    db.flush()
    log_activity(db, "user", "project.created", "project", project.id, f"Created project {project.name}")
    db.commit()
    return _serialize(project, db)


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return _serialize(project, db)


@router.put("/{project_id}")
def update_project(project_id: str, payload: ProjectIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    data = payload.model_dump()
    if data.get("client_id") and db.get(Client, data["client_id"]) is None:
        raise HTTPException(status_code=400, detail="client not found")
    for key, value in data.items():
        setattr(project, key, value)
    log_activity(db, "user", "project.updated", "project", project.id, f"Updated project {project.name}")
    db.commit()
    return _serialize(project, db)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    project.status = "cancelled"
    db.commit()


# ---- milestones ----
@router.post("/{project_id}/milestones", status_code=201)
def add_milestone(project_id: str, payload: MilestoneIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    milestone = ProjectMilestone(project_id=project_id, **payload.model_dump())
    db.add(milestone)
    log_activity(db, "user", "milestone.created", "milestone", milestone.id, f"Milestone '{milestone.title}' added")
    db.commit()
    db.refresh(milestone)
    return {"id": milestone.id, "project_id": milestone.project_id, "title": milestone.title,
            "due_date": milestone.due_date.isoformat() if milestone.due_date else None, "status": milestone.status}


@router.patch("/{project_id}/milestones/{milestone_id}")
def update_milestone(project_id: str, milestone_id: str, payload: MilestoneIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    milestone = db.get(ProjectMilestone, milestone_id)
    if milestone is None or milestone.project_id != project_id:
        raise HTTPException(status_code=404, detail="milestone not found")
    for key, value in payload.model_dump().items():
        setattr(milestone, key, value)
    db.commit()
    return {"id": milestone.id, "project_id": milestone.project_id, "title": milestone.title,
            "due_date": milestone.due_date.isoformat() if milestone.due_date else None, "status": milestone.status}
