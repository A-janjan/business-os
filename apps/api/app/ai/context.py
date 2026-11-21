"""Context retrieval for AI agents.

Builds a grounding bundle from the database. Everything included is drawn from
authoritative records — agents must never invent figures not present here.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    ActivityLog,
    BusinessReport,
    Client,
    FinancialTransaction,
    Invoice,
    Project,
    Task,
    KnowledgeDocument,
)


def build_context(db: Session, *, project_id: str | None = None, client_id: str | None = None) -> dict[str, Any]:
    today = date.today()
    month_start = today.replace(day=1)
    month_end = (today.replace(day=28) + timedelta(days=4)).replace(day=1)

    active_projects = list(db.scalars(select(Project).where(Project.status == "active").limit(10)))
    overdue_tasks = list(db.scalars(
        select(Task).where(Task.status.notin_(["done", "archived"]), Task.due_date < today).limit(10)
    ))
    pending_tasks = list(db.scalars(select(Task).where(Task.status.notin_(["done", "archived"])).limit(10)))

    month_income = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
        FinancialTransaction.kind == "income",
        FinancialTransaction.date >= month_start,
        FinancialTransaction.date < month_end,
    ))
    month_expense = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
        FinancialTransaction.kind == "expense",
        FinancialTransaction.date >= month_start,
        FinancialTransaction.date < month_end,
    ))

    client_revenue = 0.0
    if client_id:
        cv = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
            FinancialTransaction.client_id == client_id, FinancialTransaction.kind == "income"
        ))
        client_revenue = float(cv or 0)

    recent_activity = list(db.scalars(
        select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(10)
    ))

    overdue_invoices = list(db.scalars(
        select(Invoice).where(Invoice.due_date < today, Invoice.status.not_in(["paid", "void"])).limit(10)
    ))

    ctx: dict[str, Any] = {
        "business_profile": {
            "today": today.isoformat(),
            "month": today.strftime("%Y-%m"),
            "active_clients": db.scalar(select(func.count(Client.id)).where(Client.status == "active")) or 0,
            "active_projects": len(active_projects),
            "pending_tasks": len(pending_tasks),
            "overdue_tasks": len(overdue_tasks),
            "month_income": float(month_income or 0),
            "month_expense": float(month_expense or 0),
            "month_net": float(month_income or 0) - float(month_expense or 0),
        },
        "active_projects": [
            {"name": p.name, "progress": float(p.progress or 0), "deadline": p.deadline.isoformat() if p.deadline else None, "priority": p.priority}
            for p in active_projects
        ],
        "overdue_tasks": [{"title": t.title, "due": t.due_date.isoformat() if t.due_date else None} for t in overdue_tasks],
        "pending_tasks": [{"title": t.title, "priority": t.priority, "due": t.due_date.isoformat() if t.due_date else None} for t in pending_tasks],
        "recent_activity": [{"summary": a.summary, "actor": a.actor, "when": a.created_at.isoformat()} for a in recent_activity],
        "overdue_invoices": [{"number": i.number, "amount": float(i.amount), "currency": i.currency, "due_date": i.due_date.isoformat() if i.due_date else None} for i in overdue_invoices],
    }

    if project_id:
        project = db.get(Project, project_id)
        if project:
            tasks = list(db.scalars(select(Task).where(Task.project_id == project_id).limit(20)))
            from ..models import ProjectMilestone
            milestones = list(db.scalars(select(ProjectMilestone).where(ProjectMilestone.project_id == project_id)))
            ctx["focused_project"] = {
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "progress": float(project.progress or 0),
                "deadline": project.deadline.isoformat() if project.deadline else None,
                "priority": project.priority,
                "tasks": [{"title": t.title, "status": t.status, "priority": t.priority} for t in tasks],
                "milestones": [{"title": m.title, "status": m.status, "due_date": m.due_date.isoformat() if m.due_date else None} for m in milestones],
            }

    if client_id:
        client = db.get(Client, client_id)
        if client:
            tasks = list(db.scalars(select(Task).where(Task.client_id == client_id).limit(20)))
            projects = list(db.scalars(select(Project).where(Project.client_id == client_id).limit(10)))
            ctx["focused_client"] = {
                "name": client.name,
                "company": client.company,
                "status": client.status,
                "total_revenue": client_revenue,
                "projects": [{"name": p.name, "status": p.status} for p in projects],
                "open_tasks": [{"title": t.title, "status": t.status} for t in tasks],
            }

    reports = list(db.scalars(select(BusinessReport).order_by(BusinessReport.created_at.desc()).limit(5)))
    ctx["recent_reports"] = [{"title": r.title, "type": r.type, "created_at": r.created_at.isoformat()} for r in reports]

    return ctx
