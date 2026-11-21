"""Finance: transactions, invoices, monthly summaries."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, log_activity
from ..models import Client, Invoice, FinancialTransaction, Project, User
from ..schemas import InvoiceIn, TransactionIn

router = APIRouter(prefix="/finance", tags=["finance"])


def _tx_serialize(t: FinancialTransaction) -> dict:
    return {
        "id": t.id, "kind": t.kind, "amount": float(t.amount or 0), "currency": t.currency,
        "category": t.category, "client_id": t.client_id, "project_id": t.project_id,
        "date": t.date.isoformat(), "description": t.description,
        "created_at": t.created_at.isoformat(),
    }


def _inv_serialize(i: Invoice) -> dict:
    return {
        "id": i.id, "number": i.number, "client_id": i.client_id,
        "amount": float(i.amount or 0), "currency": i.currency,
        "due_date": i.due_date.isoformat() if i.due_date else None,
        "status": i.status, "paid_date": i.paid_date.isoformat() if i.paid_date else None,
        "description": i.description,
        "created_at": i.created_at.isoformat(), "updated_at": i.updated_at.isoformat(),
    }


@router.get("/transactions")
def list_transactions(
    kind: str = "",
    category: str = "",
    start: str = "",
    end: str = "",
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(FinancialTransaction).order_by(FinancialTransaction.date.desc(), FinancialTransaction.created_at.desc())
    if kind:
        stmt = stmt.where(FinancialTransaction.kind == kind)
    if category:
        stmt = stmt.where(FinancialTransaction.category == category)
    if start:
        stmt = stmt.where(FinancialTransaction.date >= date.fromisoformat(start))
    if end:
        stmt = stmt.where(FinancialTransaction.date <= date.fromisoformat(end))
    stmt = stmt.limit(limit)
    items = list(db.scalars(stmt))
    return {"items": [_tx_serialize(t) for t in items], "total": len(items)}


@router.post("/transactions", status_code=201)
def create_transaction(payload: TransactionIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    data = payload.model_dump()
    if data.get("client_id") and db.get(Client, data["client_id"]) is None:
        raise HTTPException(status_code=400, detail="client not found")
    if data.get("project_id") and db.get(Project, data["project_id"]) is None:
        raise HTTPException(status_code=400, detail="project not found")
    if data.get("date") is None:
        data["date"] = date.today()
    tx = FinancialTransaction(**data)
    db.add(tx)
    db.flush()
    log_activity(db, "user", "transaction.created", "transaction", tx.id, f"{tx.kind}: {tx.amount} {tx.currency}")
    db.commit()
    return _tx_serialize(tx)


@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    tx = db.get(FinancialTransaction, tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    db.delete(tx)
    db.commit()


@router.get("/invoices")
def list_invoices(
    status: str = "", db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    stmt = select(Invoice).order_by(Invoice.due_date.nullslast(), Invoice.created_at.desc())
    if status:
        stmt = stmt.where(Invoice.status == status)
    items = list(db.scalars(stmt))
    overdue_count = 0
    for i in items:
        if i.status not in ("paid", "void") and i.due_date and i.due_date < date.today():
            i.status = "overdue"
            overdue_count += 1
    if overdue_count:
        db.commit()
    return {"items": [_inv_serialize(i) for i in items], "total": len(items), "overdue": overdue_count}


@router.post("/invoices", status_code=201)
def create_invoice(payload: InvoiceIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    data = payload.model_dump()
    if data.get("client_id") and db.get(Client, data["client_id"]) is None:
        raise HTTPException(status_code=400, detail="client not found")
    if db.scalar(select(Invoice).where(Invoice.number == data["number"])):
        raise HTTPException(status_code=409, detail="invoice number already exists")
    inv = Invoice(**data)
    db.add(inv)
    db.flush()
    log_activity(db, "user", "invoice.created", "invoice", inv.id, f"Invoice {inv.number}: {inv.amount} {inv.currency}")
    db.commit()
    return _inv_serialize(inv)


@router.put("/invoices/{invoice_id}")
def update_invoice(invoice_id: str, payload: InvoiceIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    data = payload.model_dump()
    dup = db.scalar(select(Invoice).where(Invoice.number == data["number"], Invoice.id != invoice_id))
    if dup:
        raise HTTPException(status_code=409, detail="invoice number already exists")
    if data.get("status") == "paid" and data.get("paid_date") is None:
        data["paid_date"] = date.today()
    for key, value in data.items():
        setattr(inv, key, value)
    db.commit()
    return _inv_serialize(inv)


@router.delete("/invoices/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    inv.status = "void"
    db.commit()


@router.get("/summary")
def summary(
    month: str = "", db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    today = date.today()
    target_month = month or today.strftime("%Y-%m")
    try:
        start = date.fromisoformat(f"{target_month}-01")
    except ValueError:
        raise HTTPException(status_code=400, detail="month must be YYYY-MM")
    from datetime import timedelta
    month_end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)

    income = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
        FinancialTransaction.kind == "income",
        FinancialTransaction.date >= start, FinancialTransaction.date < month_end,
    ))
    expenses = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
        FinancialTransaction.kind == "expense",
        FinancialTransaction.date >= start, FinancialTransaction.date < month_end,
    ))
    invoice_due = db.scalar(select(func.coalesce(func.sum(Invoice.amount), 0)).where(
        Invoice.status.not_in(["paid", "void"])
    ))
    open_invoices = list(db.scalars(select(Invoice).where(Invoice.status.not_in(["paid", "void"]))))
    overdue = [i for i in open_invoices if i.due_date and i.due_date < today]
    return {
        "month": target_month,
        "income": float(income or 0),
        "expenses": float(expenses or 0),
        "net": float(income or 0) - float(expenses or 0),
        "open_invoice_amount": float(invoice_due or 0),
        "overdue_invoices": len(overdue),
    }

