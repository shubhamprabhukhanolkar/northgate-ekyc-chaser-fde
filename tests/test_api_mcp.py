import pytest
from contextlib import contextmanager
from fastapi.testclient import TestClient
from jsonschema import validate
from app.main import app
from app.mcp.server import mcp, approve_or_discard_draft
from app.db import rows, connect
from app.worker import scan_nudges


@contextmanager
def client_context():
    # The official MCP session manager is single-use. Only the HTTP MCP test
    # runs application lifespan; other routes use the isolated seeded DB directly.
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()


def test_api_auth_roles_and_received_race():
    with client_context() as client:
        assert client.get("/api/cases").status_code == 401
        login = client.post("/api/auth/login", json={"email": "rm@northgate.demo", "password": "NorthgateDemo!2026"})
        assert login.status_code == 200
        assert "HttpOnly" in login.headers["set-cookie"]
        assert len(client.get("/api/cases").json()) == 42
        cid = "NG-2026-0841"
        assert client.post(f"/api/cases/{cid}/generate").status_code == 409
        assert client.get(f"/api/cases/{cid}").status_code == 200
        result = client.post(f"/api/cases/{cid}/generate")
        assert result.status_code == 200, result.text
        assert result.json()["scorecard"]["passed"]
        assert client.put("/api/runtime/outage", json={"enabled": True}).status_code == 403
        assert client.post(f"/api/cases/{cid}/documents/ubo/receive").status_code == 403
        token = client.post(f"/api/cases/{cid}/mcp-approval-token").json()["approval_token"]
        decision = approve_or_discard_draft(cid, "approve_send", rm_approval_token=token)
        assert decision["transport"] == "synthetic_outbox"


def test_mcp_bearer_required(monkeypatch):
    security = mcp.settings.transport_security
    monkeypatch.setattr(security, "allowed_hosts", security.allowed_hosts+["northgate.example.run.app"])
    with TestClient(app) as client:
        assert client.post("/mcp/", json={}).status_code == 401
        response = client.post("/mcp/", headers={"Authorization": "Bearer test-mcp-key", "Accept": "application/json, text/event-stream"},
                               json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "1"}}})
        assert response.status_code == 200, response.text
        assert response.json()["result"]["serverInfo"]["name"] == "Northgate eKYC"
        payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        headers = {"Authorization": "Bearer test-mcp-key", "Accept": "application/json, text/event-stream", "Host": "northgate.example.run.app"}
        hosted = client.post("/mcp/", headers=headers, json=payload)
        assert hosted.status_code == 200, hosted.text
        headers["Host"] = "untrusted.example.run.app"
        assert client.post("/mcp/", headers=headers, json=payload).status_code == 421


async def test_mcp_tools_validate_schemas_and_results():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    assert len(tools) == 7
    for name, args in [("list_onboarding_cases", {}), ("get_case_gap_checklist", {"case_id": "NG-2026-0841"}),
                       ("generate_chase_draft", {"case_id": "NG-2026-0841"}), ("get_finops_cost_summary", {})]:
        validate(args, tools[name].inputSchema)
        content, structured = await mcp.call_tool(name, args)
        assert content
        validate(structured, tools[name].outputSchema)
    assert rows("SELECT * FROM drafts")[0]["status"] == "REVIEW"
    assert not rows("SELECT * FROM outbox")
    result = approve_or_discard_draft("NG-2026-0841", "approve_send")
    assert result["requires_human_approval"]


def test_nudge_scheduler_never_sends_and_suppresses_replies():
    with connect() as db:
        db.execute("UPDATE cases SET nudge_due=0 WHERE last_sent_at IS NOT NULL")
        db.execute("UPDATE cases SET replied_at='2026-01-01T00:00:00+00:00' WHERE id='NG-2026-0844'")
    assert scan_nudges() == 2
    assert scan_nudges() == 0
    assert not rows("SELECT * FROM outbox")


def test_prompt_save_requires_exact_passing_regression():
    with client_context() as client:
        client.post("/api/auth/login", json={"email": "admin@northgate.demo", "password": "NorthgateDemo!2026"})
        active = client.get("/api/prompts").json()["active"]
        candidate = {"prompts": {k: {"content": v["content"], "settings": v["settings"]} for k, v in active.items()}}
        assert client.put("/api/prompts", json=candidate).status_code == 409
        tested = client.post("/api/prompts/test", json=candidate)
        assert tested.status_code == 200 and tested.json()["passed"], tested.text
        candidate["regression_id"] = tested.json()["id"]
        candidate["prompts"]["toner"]["settings"]["formality"] = 33
        assert client.put("/api/prompts", json=candidate).status_code == 409
        candidate["prompts"]["toner"]["settings"]["formality"] = 75
        assert client.put("/api/prompts", json=candidate).status_code == 200


def test_cross_origin_mutation_blocked():
    with client_context() as client:
        assert client.post("/api/auth/login", headers={"Origin": "https://evil.example"}, json={"email": "rm@northgate.demo", "password": "NorthgateDemo!2026"}).status_code == 403
