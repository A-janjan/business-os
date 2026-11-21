"""Shared test fixtures: isolated SQLite DB + vault in a temp dir."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Configure environment BEFORE importing the app.
_TMP = tempfile.mkdtemp(prefix="business-os-test-")
_DB = Path(_TMP) / "test.db"
_VAULT = Path(_TMP) / "vault"

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["KNOWLEDGE_DIR"] = str(_VAULT)
os.environ["AUTH_SECRET"] = "test-secret-not-for-production-long-enough-for-sha256"
os.environ["AI_ENABLED"] = "true"  # enabled, but no base URL -> 'not configured' mode
os.environ["ADMIN_BOOTSTRAP"] = "false"

# make `app` importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


ADMIN_EMAIL = "admin@test.local"
ADMIN_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def auth_headers(client):
    """Bootstrap the admin user (first run) and return auth headers."""
    r = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        r = client.post("/api/auth/register", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "name": "Admin"
        })
        assert r.status_code in (200, 201), r.text
    else:
        pass
    r = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def vault_dir():
    _VAULT.mkdir(parents=True, exist_ok=True)
    yield _VAULT


@pytest.fixture
def client_and_token(client):
    """Fresh client session with token; vault cleared."""
    r = client.get("/api/auth/me")
    # ensure the admin user exists
    if r.status_code != 200:
        client.post("/api/auth/register", json={
            "email": "admin@test.local", "password": "correct-horse-battery-staple", "name": "Admin"
        })
    r = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "correct-horse-battery-staple"})
    token = r.json()["access_token"]
    yield client, {"Authorization": f"Bearer {token}"}


def teardown_module_session():
    # nothing to clean up between runs; temp dir lives per-test-session
    pass


# cleanup hooks
def pytest_sessionfinish(session):
    shutil.rmtree(_TMP, ignore_errors=True)
