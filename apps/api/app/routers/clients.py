"""Clients CRUD."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, log_activity
from ..models import Client, FinancialTransaction
from ..schemas import ClientIn, ClientOut
from ..models import User

router = APIRouter(prefix="/clients", tags=["clients"])


def _with_revenue(client: Client, db: Session) -> dict:
    total = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
        FinancialTransaction.client_id == client.id, FinancialTransaction.kind == "income"
    ))
    return {
        "id": client.id, "name": client.name, "company": client.company, "status": client.status,
        "email": client.email, "phone": client.phone, "address": client.address,
        "payment_terms": client.payment_terms, "contract_notes": client.contract_notes,
        "notes": client.notes, "created_at": client.created_at, "updated_at": client.updated_at,
        "revenue_total": float(total or 0),
    }


@router.get("/")
def list_clients(
    status: str = "", db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    stmt = select(Client).order_by(Client.name)
    if status:
        stmt = stmt.where(Client.status == status)
    items = list(db.scalars(stmt))
    return {"items": [_with_revenue(c, db) for c in items], "total": len(items)}


@router.post("/", status_code=201)
def create_client(payload: ClientIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    client = Client(**payload.model_dump())
    db.add(client)
    log_activity(db, "user", "client.created", "client", client.id, f"Created client {client.name}")
    db.commit()
    db.refresh(client)
    return _with_revenue(client, db)


@router.get("/{client_id}")
def get_client(client_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    return _with_revenue(client, db)


@router.put("/{client_id}")
def update_client(client_id: str, payload: ClientIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    for key, value in payload.model_dump().items():
        setattr(client, key, value)
    log_activity(db, "user", "client.updated", "client", client.id, f"Updated client {client.name}")
    db.commit()
    db.refresh(client)
    return _with_revenue(client, db)


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.status = "churned"
    db.commit()
