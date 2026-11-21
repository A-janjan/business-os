"""Dashboard summary."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import (
    ActivityLog, AIExecution, Client, FinancialTransaction, Invoice, Project, Task, User,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = date.today()
    month_start = today.replace(day=1)
    month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    active_projects = db.scalar(select(func.count(Project.id)).where(Project.status == "active")) or 0
    overdue_tasks = db.scalar(select(func.count(Task.id)).where(
        Task.status.notin_(["done", "archived"]), Task.due_date < today)) or 0
    pending_tasks = db.scalar(select(func.count(Task.id)).where(
        Task.status.notin_(["done", "archived"]))) or 0
    active_clients = db.scalar(select(func.count(Client.id)).where(Client.status == "active")) or 0

    month_income = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
        FinancialTransaction.kind == "income",
        FinancialTransaction.date >= month_start, FinancialTransaction.date < month_end)) or 0
    month_expense = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
        FinancialTransaction.kind == "expense",
        FinancialTransaction.date >= month_start, FinancialTransaction.date < month_end)) or 0

    upcoming_tasks = list(db.scalars(
        select(Task).where(Task.status.notin_(["done", "archived"]), Task.due_date >= today)
        .order_by(Task.due_date).limit(5)))

    upcoming_deadlines = list(db.scalars(
        select(Project).where(Project.deadline >= today, Project.status.not_in(["completed", "cancelled"]))
        .order_by(Project.deadline).limit(5)))

    overdue_invoices = list(db.scalars(
        select(Invoice).where(Invoice.due_date < today, Invoice.status.not_in(["paid", "void"])).limit(5)))

    recent_activity = list(db.scalars(select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(8)))

    recent_ai = list(db.scalars(select(AIExecution).order_by(AIExecution.created_at.desc()).limit(5)))

    due_in_14 = today + timedelta(days=14)
    upcoming_deadlines_detail = [
        {"id": p.id, "name": p.name, "deadline": p.deadline.isoformat(), "days_left": (p.deadline - today).days}
        for p in upcoming_deadlines if p.deadline
    ]

    return {
        "today": today.isoformat(),
        "active_projects": active_projects,
        "active_clients": active_clients,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
        "month_income": float(month_income),
        "month_expense": float(month_expense),
        "month_net": float(month_income) - float(month_expense),
        "upcoming_tasks": [{
            "id": t.id, "title": t.title, "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "status": t.status} for t in upcoming_tasks],
        "upcoming_deadlines": upcoming_deadlines_detail,
        "overdue_invoices": [{
            "id": i.id, "number": i.number, "amount": float(i.amount), "currency": i.currency,
            "due_date": i.due_date.isoformat() if i.due_date else None} for i in overdue_invoices],
        "recent_activity": [{
            "id": a.id, "actor": a.actor, "summary": a.summary, "entity_type": a.entity_type,
            "created_at": a.created_at.isoformat()} for a in recent_activity],
        "recent_ai_executions": [{
            "id": e.id, "agent": e.agent, "status": e.status,
            "created_at": e.created_at.isoformat()} for e in recent_ai],
    }
