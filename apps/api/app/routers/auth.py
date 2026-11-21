"""Auth routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password, verify_password
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    settings = get_settings()
    user_count = db.scalar(select(func.count(User.id))) or 0
    if user_count > 0 and not settings.admin_bootstrap:
        raise HTTPException(status_code=403, detail="registration disabled after bootstrap")
    existing = db.scalars(select(User).where(User.email == payload.email.lower())).first()
    if existing:
        raise HTTPException(status_code=409, detail="email already registered")
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="admin" if user_count == 0 else "member",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalars(select(User).where(User.email == payload.email.lower())).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
