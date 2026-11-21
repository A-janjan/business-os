"""Authentication: argon2 hashing + JWT.

The app is designed as a single-tenant personal system: the first registered
user becomes the administrator. After bootstrap no further registrations are
allowed via the public endpoint (set ADMIN_BOOTSTRAP=true to re-enable in dev).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    expires = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + expires,
    }
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
