"""Research documents."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, log_activity
from ..models import ResearchDocument, User
from ..schemas import ResearchIn

router = APIRouter(prefix="/research", tags=["research"])


def _serialize(r: ResearchDocument) -> dict:
    return {
        "id": r.id, "title": r.title, "source_urls": r.source_urls or [],
        "summary": r.summary, "tags": r.tags or [], "related_projects": r.related_projects or [],
        "created_from": r.created_from,
        "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat(),
    }


@router.get("/")
def list_research(tag: str = "", db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(ResearchDocument).order_by(ResearchDocument.updated_at.desc())
    items = list(db.scalars(stmt))
    if tag:
        items = [r for r in items if tag in (r.tags or [])]
    return {"items": [_serialize(r) for r in items], "total": len(items)}


@router.post("/", status_code=201)
def create_research(payload: ResearchIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = ResearchDocument(**payload.model_dump())
    db.add(r)
    db.flush()
    log_activity(db, "user", "research.created", "research", r.id, f"Research '{r.title}' added")
    db.commit()
    return _serialize(r)


@router.get("/{research_id}")
def get_research(research_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = db.get(ResearchDocument, research_id)
    if r is None:
        raise HTTPException(status_code=404, detail="research not found")
    return _serialize(r)


@router.put("/{research_id}")
def update_research(research_id: str, payload: ResearchIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = db.get(ResearchDocument, research_id)
    if r is None:
        raise HTTPException(status_code=404, detail="research not found")
    for key, value in payload.model_dump().items():
        setattr(r, key, value)
    db.commit()
    return _serialize(r)


@router.delete("/{research_id}", status_code=204)
def delete_research(research_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = db.get(ResearchDocument, research_id)
    if r is None:
        raise HTTPException(status_code=404, detail="research not found")
    db.delete(r)
    db.commit()
