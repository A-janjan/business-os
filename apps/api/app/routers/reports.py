"""Reports: deterministic weekly review + AI-backed daily brief."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user, log_activity
from ..knowledge.repository import Repository
from ..models import ActivityLog, BusinessReport, Client, FinancialTransaction, Invoice, Project, Task, User
from ..schemas import ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=dict)
def list_reports(type: str = "", db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(BusinessReport).order_by(BusinessReport.created_at.desc()).limit(100)
    if type:
        stmt = stmt.where(BusinessReport.type == type)
    items = [
        {"id": r.id, "type": r.type, "title": r.title, "body": r.body, "source": r.source or {}, "agent": r.agent,
         "created_at": r.created_at.isoformat()}
        for r in db.scalars(stmt)
    ]
    return {"items": items, "total": len(items)}


@router.get("/{report_id}", response_model=dict)
def get_report(report_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = db.get(BusinessReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="report not found")
    return {"id": r.id, "type": r.type, "title": r.title, "body": r.body, "source": r.source or {},
            "agent": r.agent, "created_at": r.created_at.isoformat()}


def _weekly_review_body(db: Session) -> dict:
    today = date.today()
    week_start = today - timedelta(days=7)

    completed = list(db.scalars(select(Task).where(Task.completed_at >= datetime.combine(week_start, datetime.min.time()))))
    created_tasks = list(db.scalars(select(Task).where(Task.created_at >= datetime.combine(week_start, datetime.min.time()))))
    completed_projects = list(db.scalars(select(Project).where(Project.updated_at >= datetime.combine(week_start, datetime.min.time()), Project.status == "completed")))
    income = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
        FinancialTransaction.kind == "income", FinancialTransaction.date >= week_start
    ))
    expenses = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
        FinancialTransaction.kind == "expense", FinancialTransaction.date >= week_start
    ))
    new_clients = db.scalar(select(func.count(Client.id)).where(Client.created_at >= datetime.combine(week_start, datetime.min.time())))
    overdue = list(db.scalars(select(Task).where(Task.status.notin_(["done", "archived"]), Task.due_date < today)))
    new_invoices = list(db.scalars(select(Invoice).where(Invoice.created_at >= datetime.combine(week_start, datetime.min.time()))))

    body = f"""# Weekly Review — {week_start.isoformat()} → {today.isoformat()}

## Highlights
- Tasks completed: {len(completed)}
- Tasks created: {len(created_tasks)}
- Income this week: {float(income or 0):.2f}
- Expenses this week: {float(expenses or 0):.2f}
- Net this week: {float(income or 0) - float(expenses or 0):.2f}
- New clients: {new_clients or 0}
- Invoices created: {len(new_invoices)}
- Completed projects: {len(completed_projects)}

## Completed work
{chr(10).join(f"- {t.title}" for t in completed[:20]) or '- (none)'}

## At risk / overdue
{chr(10).join(f"- {t.title} (due {t.due_date.isoformat() if t.due_date else '?'})" for t in overdue[:10]) or '- (none)'}

## Recommendations (deterministic)
- {'Review overdue tasks above and re-prioritize.' if overdue else 'No overdue tasks. Keep cadence.'}
- {'Focus on projects with the closest deadlines.' if any(p.deadline for p in db.scalars(select(Project).where(Project.status == 'active'))) else 'No active projects with deadlines — plan next milestones.'}
- {'Renew or follow up on {n} clients.'.format(n=len(list(db.scalars(select(Client).where(Client.status == 'active'))))) if (db.scalar(select(func.count(Client.id)).where(Client.status == 'active')) or 0) > 0 else 'Onboard new clients.'}
"""
    return {"body": body, "week_start": week_start.isoformat(), "week_end": today.isoformat(),
            "completed_tasks": len(completed), "created_tasks": len(created_tasks),
            "income": float(income or 0), "expenses": float(expenses or 0),
            "new_clients": int(new_clients or 0), "overdue_tasks": len(overdue)}


@router.post("/weekly-review", status_code=201)
def create_weekly_review(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    data = _weekly_review_body(db)
    report = BusinessReport(type="weekly-review", title=f"Weekly Review — {data['week_start']} → {data['week_end']}",
                            body=data["body"], source=data, agent="system")
    db.add(report)
    db.flush()

    # best-effort save as markdown artifact (never fails the report)
    try:
        repo = Repository(get_settings().knowledge_dir)
        path = f"09-GENERATED/Reports/{date.today().isoformat()}-weekly-review.md"
        try:
            repo.create(path, {"title": report.title, "type": "weekly-review", "generated": True}, report.body)
        except Exception:
            pass
    except Exception:
        pass

    log_activity(db, "system", "report.weekly_review", "report", report.id, "Weekly review generated")
    db.commit()
    db.refresh(report)
    return {"id": report.id, "type": report.type, "title": report.title, "body": report.body,
            "source": report.source, "agent": report.agent, "created_at": report.created_at.isoformat()}


@router.post("/daily-brief", status_code=201)
async def create_daily_brief(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """AI-powered daily brief. Explicitly fails when no provider is configured."""
    from ..ai.providers import get_provider
    from ..ai.agents import AgentExecutor
    from ..ai.context import build_context

    provider = get_provider()
    if not provider.is_configured:
        raise HTTPException(status_code=503, detail="AI provider not configured — set AI_BASE_URL/AI_MODEL in .env")

    context = build_context(db)
    executor = AgentExecutor(provider, temperature=get_settings().ai_temperature, max_tokens=get_settings().ai_max_tokens)
    result = await executor.run(
        "executive-assistant",
        input={"task": "daily-brief"},
        question="Generate today's daily business brief: priorities, risks, opportunities, recommended actions.",
        context=context,
    )
    if result.status != "success":
        raise HTTPException(status_code=502, detail=f"AI execution failed: {result.error}")

    body = f"# Daily Business Brief — {date.today().isoformat()}\n\n```json\n{result.output}\n```"
    report = BusinessReport(type="daily-brief", title=f"Daily Business Brief — {date.today().isoformat()}",
                            body=body, source={"execution": result.agent}, agent=result.agent)
    db.add(report)
    log_activity(db, "ai", "report.daily_brief", "report", report.id, "AI daily brief generated")
    db.commit()
    db.refresh(report)
    return {"id": report.id, "type": report.type, "title": report.title, "body": report.body,
            "source": report.source, "agent": report.agent, "created_at": report.created_at.isoformat()}
