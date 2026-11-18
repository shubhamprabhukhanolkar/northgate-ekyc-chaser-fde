from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.finance import financial_summary
from app.db import connect, rows, now


def sign_in(client, role):
    response = client.post("/api/auth/login", json={"email": f"{role}@northgate.demo", "password": "NorthgateDemo!2026"})
    assert response.status_code == 200, response.text
    return response.json()


def test_cfo_account_is_separate_read_only_and_report_calls_no_ai(monkeypatch):
    from app.llm.router import router
    agent = AsyncMock(side_effect=AssertionError("Financial dashboard must not invoke AI"))
    monkeypatch.setattr(router, "call", agent)
    client = TestClient(app)
    assert client.get("/api/cfo/summary").status_code == 401
    assert sign_in(client, "cfo")["user"]["role"] == "cfo"
    assert client.get("/api/auth/me").json()["role"] == "cfo"
    before = len(rows("SELECT * FROM cost_ledger"))
    response = client.get("/api/cfo/summary")
    assert response.status_code == 200, response.text
    assert response.json()["totals"]["average_case_cost_gbp"] is None
    assert response.json()["activity"]["case_inventory"] == 42
    assert len(rows("SELECT * FROM cost_ledger")) == before
    for method, url, body in [
        ("GET", "/api/cases", None), ("GET", "/api/prompts", None),
        ("POST", "/api/policy/query", {"question": "Generate an email"}),
        ("POST", "/api/cases/NG-2026-0841/generate", {}),
        ("POST", "/api/cases/NG-2026-0841/runs", {"mode": "auto"}),
        ("PUT", "/api/runtime/outage", {"enabled": True}),
        ("GET", "/api/mcp/connections", None),
    ]:
        assert client.request(method, url, json=body).status_code == 403, url
    assert client.get("/api/runtime").status_code == 200
    assert not agent.called
    assert client.get("/api/cfo/summary?days=8").status_code == 422
    client.post("/api/auth/logout")
    assert client.get("/api/cfo/summary").status_code == 401
    sign_in(client, "rm")
    assert client.get("/api/cfo/summary").status_code == 403
    sign_in(client, "admin")
    for days in (0, 7, 30, 90):
        assert client.get(f"/api/cfo/summary?days={days}").status_code == 200
    client.close()


def test_financial_costs_denominators_dates_and_failovers():
    current = datetime.now(timezone.utc)
    sample = [
        ("orchestrator", "gemini", 100, 50, 100, .5, .4, "NG-2026-0841", now(), "success", 0),
        ("drafter", "groq", 30, 20, 300, .25, .2, "NG-2026-0841", now(), "success", 1),
        ("critique", "gemini", 0, 0, 900, 0, 0, "NG-2026-0842", now(), "error", 0),
        ("policy_copilot", "gemini", 20, 10, 200, .125, .1, None, now(), "success", 0),
        ("drafter", "offline_demo", 0, 0, 0, 0, 0, "NG-2026-0843", now(), "fixture", 0),
        ("drafter", "gemini", 10, 5, 100, 2.5, 2, "NG-2026-0843", (current-timedelta(days=120)).isoformat(), "success", 0),
        ("drafter", "gemini", 10, 5, 100, 12.5, 10, "NG-2026-0843", (current+timedelta(days=1)).isoformat(), "success", 0),
    ]
    with connect() as db:
        db.executemany("INSERT INTO cost_ledger(agent_name,provider,prompt_tokens,completion_tokens,latency_ms,cost_usd,cost_gbp,case_id,created_at,status,failover) VALUES(?,?,?,?,?,?,?,?,?,?,?)", sample)
    report = financial_summary(30)
    totals = report["totals"]
    assert totals["calls"] == 4
    assert totals["cost_gbp"] == pytest.approx(.7)
    assert totals["case_cost_gbp"] == pytest.approx(.6)
    assert totals["non_case_cost_gbp"] == pytest.approx(.1)
    assert totals["average_case_cost_gbp"] == pytest.approx(.3)
    assert totals["average_call_cost_gbp"] == pytest.approx(.175)
    assert totals["costed_cases"] == 2
    assert totals["failovers"] == 1
    assert totals["error_rate"] == .25
    assert totals["average_latency_ms"] == 375
    assert totals["p95_latency_ms"] == 900
    assert totals["offline_fixture_calls"] == 1
    assert totals["prompt_tokens"] == 150 and totals["completion_tokens"] == 80
    assert sum(row["cost_gbp"] for row in report["daily"]) == pytest.approx(.7)
    assert len(report["daily"]) == 30
    assert report["jurisdictions"]["SG"]["cost_gbp"] == pytest.approx(.6)
    assert report["jurisdictions"]["UK"]["costed_cases"] == 1
    assert sum(provider["cost_gbp"] for provider in report["providers"]) == pytest.approx(.7)
    assert financial_summary(0)["totals"]["cost_gbp"] == pytest.approx(2.7)
    assert len(financial_summary(0)["daily"]) <= 90
    assert "contact" not in str(report) and "password" not in str(report)


def test_empty_financial_report_has_no_fabricated_activity_or_savings():
    report = financial_summary(7)
    assert report["totals"]["cost_gbp"] == 0
    assert report["totals"]["costed_cases"] == 0
    assert report["totals"]["average_case_cost_gbp"] is None
    assert report["totals"]["average_call_cost_gbp"] is None
    assert report["totals"]["p95_latency_ms"] is None
    assert report["providers"] == [] and report["agents"] == []
    assert report["activity"]["generated"] == 0
    assert report["activity"]["discard_rate"] is None
    assert len(report["daily"]) == 7
    assert all(row["cost_gbp"] == 0 for row in report["daily"])


def test_cfo_cannot_link_a_case_reading_oauth_client():
    from test_mcp_readonly import begin_connection
    import re
    client = TestClient(app)
    _, consent = begin_connection(client)
    request_id = re.search(r'name="request_id" value="([^"]+)"', consent.text)[1]
    response = client.post("/oauth/authorize", data={"request_id": request_id, "decision": "allow", "email": "cfo@northgate.demo", "password": "NorthgateDemo!2026"})
    assert response.status_code == 400
    assert response.json()["error"] == "access_denied"
    assert not rows("SELECT * FROM mcp_grants")
    client.close()
