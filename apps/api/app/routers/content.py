"""Content operations."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, log_activity
from ..models import ContentItem, User
from ..schemas import ContentIn

router = APIRouter(prefix="/content", tags=["content"])

VALID_STATUSES = {"idea", "draft", "review", "scheduled", "published", "archived"}


def _serialize(c: ContentItem) -> dict:
    return {
        "id": c.id, "title": c.title, "platform": c.platform, "format": c.format,
        "status": c.status, "body": c.body,
        "scheduled_for": c.scheduled_for.isoformat() if c.scheduled_for else None,
        "published_url": c.published_url, "performance": c.performance or {},
        "tags": c.tags or [], "notes": c.notes,
        "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat(),
    }


@router.get("/")
def list_content(
    status: str = "", db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    stmt = select(ContentItem).order_by(ContentItem.updated_at.desc())
    if status:
        stmt = stmt.where(ContentItem.status == status)
    items = [_serialize(c) for c in db.scalars(stmt)]
    return {"items": items, "total": len(items)}


@router.post("/", status_code=201)
def create_content(payload: ContentIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    data = payload.model_dump()
    if data["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="unknown status")
    item = ContentItem(**data)
    db.add(item)
    db.flush()
    log_activity(db, "user", "content.created", "content", item.id, f"Created content '{item.title}'")
    db.commit()
    return _serialize(item)


@router.get("/{content_id}")
def get_content(content_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="content not found")
    return _serialize(item)


@router.put("/{content_id}")
def update_content(content_id: str, payload: ContentIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="content not found")
    data = payload.model_dump()
    if data["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="unknown status")
    for key, value in data.items():
        setattr(item, key, value)
    log_activity(db, "user", "content.updated", "content", item.id, f"Updated content '{item.title}'")
    db.commit()
    return _serialize(item)


@router.patch("/{content_id}/status")
def set_status(content_id: str, payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="content not found")
    new_status = str(payload.get("status", ""))
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="unknown status")
    # AI/published-content gate: nothing auto-publishes without an explicit human update.
    item.status = new_status
    db.commit()
    return _serialize(item)


@router.delete("/{content_id}", status_code=204)
def delete_content(content_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="content not found")
    item.status = "archived"
    db.commit()
