"""Approval manager: human-in-the-loop gate for consequential AI actions.

Never bypass: anything irreversible or external-facing goes through here.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ApprovalRequest

APPROVAL_TYPES = {
    "content-draft",       # AI-generated content awaiting human review before being saved
    "publish-content",     # publishing content to a platform
    "send-email",          # sending any external message
    "delete-record",       # destructive deletes the user requested to be undoable
}


class ApprovalError(Exception):
    pass


def create_approval(db: Session, type_: str, payload: dict) -> ApprovalRequest:
    if type_ not in APPROVAL_TYPES:
        raise ApprovalError(f"unknown approval type: {type_}")
    req = ApprovalRequest(type=type_, payload=payload, status="pending")
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def list_approvals(db: Session, status: str | None = None) -> list[ApprovalRequest]:
    stmt = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc()).limit(100)
    if status:
        stmt = stmt.where(ApprovalRequest.status == status)
    return list(db.scalars(stmt))


def resolve_approval(db: Session, approval_id: str, decision: str, reason: str = "") -> ApprovalRequest:
    req = db.get(ApprovalRequest, approval_id)
    if req is None:
        raise ApprovalError("approval not found")
    if req.status != "pending":
        raise ApprovalError(f"approval already {req.status}")
    if decision not in ("approved", "rejected"):
        raise ApprovalError("decision must be 'approved' or 'rejected'")
    req.status = decision
    req.reason = reason
    db.commit()
    db.refresh(req)
    return req
