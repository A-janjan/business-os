"""Auth: registration bootstrap rules, login, token handling."""


def test_register_bootstrap_allowed(client, auth_headers):
    # bootstrap worked; /me returns the admin
    r = client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "admin@test.local"
    assert body["role"] == "admin"


def test_login_wrong_password(client, auth_headers):
    r = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "wrong-password"})
    assert r.status_code == 401


def test_me_requires_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_duplicate_registration_rejected(client, auth_headers):
    r = client.post("/api/auth/register", json={
        "email": "admin@test.local", "password": "another-password-123", "name": "Dup"
    })
    # either 403 (bootstrap closed) or 409 (duplicate) — both are correct
    assert r.status_code in (403, 409)


def test_protected_route_requires_token(client):
    r = client.get("/api/clients/")
    assert r.status_code == 401


def test_dashboard_requires_token(client):
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 401
