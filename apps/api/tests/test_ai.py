"""AI layer: honest 'not configured' behavior, structured-output validation,
approval gates, and queue lifecycle — using a scripted fake provider."""

from __future__ import annotations

import json

import pytest


def test_agents_not_configured(client_and_token):
    c, headers = client_and_token
    r = c.post("/api/ai/ask", headers=headers, json={"question": "What should I focus on?"})
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"].lower()


def test_agent_listing_works(client_and_token):
    c, headers = client_and_token
    r = c.get("/api/ai/agents", headers=headers)
    assert r.status_code == 200
    names = {a["name"] for a in r.json()["items"]}
    for expected in ["executive-assistant", "business-analyst", "project-manager", "client-intelligence", "content", "financial-analyst", "research"]:
        assert expected in names


def test_content_agent_requires_approval(client_and_token, monkeypatch):
    c, headers = client_and_token

    class FakeProvider:
        name = "scripted"
        model = "fake-1"

        @property
        def is_configured(self):
            return True

        async def complete(self, system, user, **_):
            from app.ai.providers import LLMResult
            return LLMResult(
                text=json.dumps({"title": "Test draft", "body": "A great post", "platform": "linkedin", "rationale": "test"}),
                tokens_in=10, tokens_out=20, provider="scripted", model="fake-1",
            )

    import app.routers.ai as ai_router
    monkeypatch.setattr(ai_router, "get_provider", lambda: FakeProvider())

    r = c.post("/api/ai/agents/content/run", headers=headers, json={
        "input": {"task": "draft"}, "question": "Write a LinkedIn post about AI agents."
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "awaiting_approval"
    assert body["approval_id"]

    # approval pending; resolve it
    r = c.post(f"/api/ai/approvals/{body['approval_id']}/resolve", headers=headers, json={
        "decision": "approved", "reason": "looks good",
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"


def test_content_agent_rejects_bad_json(client_and_token, monkeypatch):
    c, headers = client_and_token

    class BadProvider:
        name = "scripted"
        model = "fake-bad"

        @property
        def is_configured(self):
            return True

        async def complete(self, system, user, **_):
            from app.ai.providers import LLMResult
            return LLMResult(text="not json at all", provider="scripted", model="fake-bad")

    import app.routers.ai as ai_router
    monkeypatch.setattr(ai_router, "get_provider", lambda: BadProvider())

    r = c.post("/api/ai/agents/content/run", headers=headers, json={"input": {}, "question": "draft"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed"
    assert "validation failed" in body["error"].lower() or "no JSON" in body["error"].lower()


def test_queue_lifecycle(client_and_token):
    c, headers = client_and_token
    r = c.post("/api/queue/", headers=headers, json={
        "type": "weekly-review", "description": "Weekly review", "priority": "normal",
    })
    assert r.status_code in (200, 201), r.text
    req = r.json()
    assert req["status"] == "pending"

    r = c.post(f"/api/queue/{req['id']}/process", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["result"].get("report_id")


def test_queue_rejects_double_processing(client_and_token):
    c, headers = client_and_token
    r = c.post("/api/queue/", headers=headers, json={"type": "weekly-review", "description": "Review"})
    req = r.json()
    c.post(f"/api/queue/{req['id']}/process", headers=headers)
    r = c.post(f"/api/queue/{req['id']}/process", headers=headers)
    # second attempt must be rejected (no duplicate processing)
    assert r.status_code == 400


def test_queue_cancel(client_and_token):
    c, headers = client_and_token
    r = c.post("/api/queue/", headers=headers, json={
        "type": "content-draft", "description": "Test draft", "input": {},
    })
    req = r.json()
    r = c.post(f"/api/queue/{req['id']}/cancel", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_automation_workflow_listed(client_and_token):
    c, headers = client_and_token
    r = c.get("/api/automation/workflows", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    names = {w["name"] for w in items}
    assert "weekly-review" in names


def test_automation_trigger_honest_failure(client_and_token):
    c, headers = client_and_token
    r = c.post("/api/automation/workflows/weekly-review/trigger", headers=headers, json={"payload": {}})
    assert r.status_code in (200, 202), r.text
    # n8n is not configured in tests -> must NOT report success
    assert r.json()["status"] == "failed"
    assert "n8n" in r.json()["error"].lower()
