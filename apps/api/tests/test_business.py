"""Business modules: clients, projects, tasks, finance, dashboard."""


def _make_client(c, headers, name="Acme Logistics"):
    r = c.post("/api/clients/", headers=headers, json={"name": name, "company": "Acme", "status": "active"})
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_client_lifecycle(client_and_token):
    c, headers = client_and_token
    r = c.get("/api/clients/", headers=headers)
    assert r.status_code == 200

    created = _make_client(c, headers)
    assert created["name"] == "Acme Logistics"

    r = c.put(f"/api/clients/{created['id']}", headers=headers, json={
        "name": "Acme Logistics", "company": "Acme", "status": "active", "email": "jane@acme.com",
    })
    assert r.status_code == 200 and r.json()["email"] == "jane@acme.com"


def test_project_with_milestone_and_task(client_and_token):
    c, headers = client_and_token
    client_rec = _make_client(c, headers, "Project Client")

    r = c.post("/api/projects/", headers=headers, json={
        "name": "Website Redesign", "client_id": client_rec["id"], "status": "active", "priority": "high",
    })
    assert r.status_code in (200, 201), r.text
    project = r.json()

    r = c.post(f"/api/projects/{project['id']}/milestones", headers=headers, json={"title": "Kickoff", "status": "todo"})
    assert r.status_code in (200, 201), r.text

    r = c.post("/api/tasks/", headers=headers, json={
        "title": "Draft homepage", "project_id": project["id"], "client_id": client_rec["id"],
        "priority": "high", "status": "todo", "due_date": "2026-12-01",
    })
    assert r.status_code in (200, 201), r.text
    task = r.json()

    r = c.patch(f"/api/tasks/{task['id']}/status", headers=headers, json={"status": "done"})
    assert r.status_code == 200
    assert r.json()["status"] == "done"


def test_task_overdue_filter(client_and_token):
    c, headers = client_and_token
    c.post("/api/tasks/", headers=headers, json={
        "title": "Overdue task", "due_date": "2020-01-01", "status": "todo",
    })
    r = c.get("/api/tasks/?overdue=true", headers=headers)
    assert r.status_code == 200
    assert any("Overdue task" in t["title"] for t in r.json()["items"])


def test_finance_flow(client_and_token):
    c, headers = client_and_token
    client_rec = _make_client(c, headers, "Finance Client")

    r = c.post("/api/finance/transactions", headers=headers, json={
        "kind": "income", "amount": 1500.00, "currency": "USD", "category": "Consulting",
        "client_id": client_rec["id"], "description": "Retainer",
    })
    assert r.status_code in (200, 201), r.text

    r = c.post("/api/finance/invoices", headers=headers, json={
        "number": "INV-001", "amount": 900.00, "currency": "USD", "client_id": client_rec["id"],
        "due_date": "2020-06-01", "status": "sent", "description": "Overdue check",
    })
    assert r.status_code in (200, 201), r.text
    invoice = r.json()

    r = c.get("/api/finance/summary?month=2020-01", headers=headers)
    assert r.status_code == 200

    r = c.get("/api/finance/invoices", headers=headers)
    items = r.json()["items"]
    overdue = [i for i in items if i["status"] == "overdue"]
    assert len(overdue) >= 1

    r = c.put(f"/api/finance/invoices/{invoice['id']}", headers=headers, json={
        "number": "INV-001", "amount": 900.00, "currency": "USD", "client_id": client_rec["id"],
        "due_date": "2026-12-01", "status": "paid",
    })
    assert r.status_code == 200 and r.json()["status"] == "paid"


def test_dashboard_summary(client_and_token):
    c, headers = client_and_token
    r = c.get("/api/dashboard/summary", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "active_projects" in body and "month_income" in body and "recent_activity" in body


def test_weekly_review_report(client_and_token):
    c, headers = client_and_token
    r = c.post("/api/reports/weekly-review", headers=headers)
    assert r.status_code in (200, 201), r.text
    assert r.json()["type"] == "weekly-review"

    r = c.get("/api/reports/", headers=headers)
    assert r.status_code == 200
    assert any(rep["type"] == "weekly-review" for rep in r.json()["items"])


def test_daily_note_flow(client_and_token):
    c, headers = client_and_token
    r = c.put("/api/notes/2026-11-22", headers=headers, json={
        "title": "Daily Note - 2026-11-22",
        "body": "# Daily Note - 2026-11-22\n\n## Completed\n- Finished API\n\n## Income\nRECEIVED: 500 USD - Client A\n\n## Tasks\n- [ ] Task one\n",
    })
    assert r.status_code == 200, r.text
    assert r.json()["path"].startswith("07-DAILY-NOTES/")

    r = c.get("/api/notes/2026-11-22", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "completed" in body["sections"]
    assert any(f.get("amount") == 500.0 for f in body["finance_lines"])
