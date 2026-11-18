from datetime import datetime, timedelta, timezone
import json
import re
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import audit, connect, now, rows
from app.risk import risk_summary


def login(client, role):
    result = client.post("/api/auth/login",json={"email":f"{role}@northgate.demo","password":"NorthgateDemo!2026"})
    assert result.status_code == 200, result.text
    return result.json()


def test_cro_login_scope_and_no_agent_calls(monkeypatch):
    from app.llm.router import router
    agent = AsyncMock(side_effect=AssertionError("CRO reports must never call agents"))
    monkeypatch.setattr(router,"call",agent)
    client = TestClient(app)
    assert client.get("/api/cro/summary").status_code == 401
    assert login(client,"cro")["user"]["role"] == "cro"
    before = len(rows("SELECT * FROM audit"))
    for days in (0,7,30,90):
        response = client.get(f"/api/cro/summary?days={days}")
        assert response.status_code == 200, response.text
        assert response.json()["period"]["days"] == days
    assert len(rows("SELECT * FROM audit")) == before
    assert not rows("SELECT * FROM cost_ledger")
    for method,url,body in [
        ("GET","/api/cfo/summary",None),("GET","/api/cases",None),("GET","/api/prompts",None),("GET","/api/audit",None),
        ("POST","/api/policy/query",{"question":"Write an email"}),
        ("POST","/api/cases/NG-2026-0841/runs",{"mode":"auto"}),
        ("POST","/api/cases/NG-2026-0841/generate",{}),
        ("PUT","/api/runtime/outage",{"enabled":True}),
        ("GET","/api/mcp/connections",None),
    ]:
        assert client.request(method,url,json=body).status_code == 403,url
    for days in (8,-1,100):
        assert client.get(f"/api/cro/summary?days={days}").status_code == 422
    assert client.get("/api/runtime").status_code == 200
    assert not agent.called
    client.post("/api/auth/logout")
    assert client.get("/api/cro/summary").status_code == 401
    for role in ("rm","cfo"):
        login(client,role)
        assert client.get("/api/cro/summary").status_code == 403
    login(client,"admin")
    assert client.get("/api/cro/summary").status_code == 200
    client.close()


def test_empty_evidence_does_not_claim_perfect_controls():
    result = risk_summary(7)
    m = result["metrics"]
    assert m["outbox_check_failure_rate"] is None
    assert m["signoff_coverage"] is None
    assert m["discard_rate"] is None and m["average_tone_score"] is None
    assert m["assessed_drafts"] == 0 and m["initial_intercepted_runs"] == 0
    assert len(result["gates"]) == 8
    assert any(row["status"] == "not evidenced" for row in result["gates"])
    assert len(result["daily"]) == 7
    assert all(row["discard_rate"] is None for row in result["daily"])
    assert result["audit"] == []
    assert result["change_control"]["latest_test_passed"] is None
    assert result["metrics"]["case_inventory"] == 42
    assert result["exception_count"] == 3  # Existing synthetic due-follow-up flags, not invented risk incidents.


def test_recorded_evidence_signoff_qa_drift_and_privacy():
    current = now()
    good = {"passed":True,"tone_score":98,"zero_false_chases":True,"all_missing_consolidated":True,"no_prohibited_claims":True,"valid_email":True,"policy_compliant":True}
    bad = {**good,"passed":False,"tone_score":90,"zero_false_chases":False,"all_missing_consolidated":False,"no_prohibited_claims":False,"policy_compliant":False}
    with connect() as db:
        for did,cid,status,card,revision in [("good","NG-2026-0841","SENT",good,1),("bad","NG-2026-0842","BLOCKED",bad,1),("stale","NG-2026-0843","REVIEW",{**good,"tone_score":99},0)]:
            db.execute("INSERT INTO drafts(id,case_id,status,scorecard,gap_revision,created_at,body) VALUES(?,?,?,?,?,?,?)",(did,cid,status,json.dumps(card),revision,current,"private-draft-canary"))
        db.execute("INSERT INTO drafts(id,case_id,status,scorecard,gap_revision,created_at) VALUES('unknown','NG-2026-0844','REVIEW','not json',1,?)",(current,))
        for oid,did,cid in [("one","good","NG-2026-0841"),("two","bad","NG-2026-0842"),("three","missing","NG-2026-0845")]:
            db.execute("INSERT INTO outbox VALUES(?,?,?,?,?)",(oid,did,cid,'{"to":"private-contact-canary"}',current))
        audit(db,"rm@northgate.demo","approve_send","NG-2026-0841",{"draft_id":"good"})
        audit(db,"mcp:integration","approve_send","NG-2026-0842",{"draft_id":"bad"})
        audit(db,"rm@northgate.demo","discard","NG-2026-0843",{"draft_id":"stale","reason":"private-reason-canary"})
        audit(db,"rm@northgate.demo","draft_edited_and_rechecked","NG-2026-0843",{"draft_id":"stale"})
        old=(datetime.now(timezone.utc)-timedelta(days=10)).isoformat()
        db.execute("INSERT INTO audit(actor,action,case_id,payload,created_at,retain_until) VALUES(?,?,?,?,?,?)",("rm@northgate.demo","discard","NG-2026-0842","{}",old,old))
        db.execute("INSERT INTO workflow_runs VALUES('run','NG-2026-0842','rm@northgate.demo','COMPLETED',?,?)",(current,current))
        for kind,value in [("node_completed",{"node":"critique","iteration":1,"scorecard":bad}),("revision",{"iteration":2}),("node_completed",{"node":"critique","iteration":2,"scorecard":good})]:
            db.execute("INSERT INTO workflow_events(run_id,kind,data,created_at) VALUES('run',?,?,?)",(kind,json.dumps(value),current))
        db.execute("INSERT INTO regression VALUES('test','digest',?,?)",(json.dumps({"passed":True,"results":[{}]*5}),current))
    report = risk_summary(7)
    m = report["metrics"]
    assert m["outbox_records"] == 3 and m["human_signed"] == 1
    assert m["signoff_coverage"] == pytest.approx(1/3)
    assert m["outbox_check_assessed"] == 2 and m["outbox_check_failures"] == 1
    assert m["outbox_check_failure_rate"] == .5 and m["missing_outbox_check_evidence"] == 1
    assert m["assessed_drafts"] == 3 and m["qa_passed"] == 2 and m["qa_failed"] == 1
    assert m["average_tone_score"] == pytest.approx((98+90+99)/3)
    assert m["discard_rate"] == pytest.approx(1/3)
    assert m["previous_discard_rate"] == 1 and m["previous_review_actions"] == 1
    assert m["edited"] == 1 and m["discard_reasons_recorded"] == 1
    assert m["initial_intercepted_runs"] == 1 and m["streamed_qa_evaluations"] == 2 and m["rewrite_events"] == 1
    assert report["intercepts"]["zero_false_chases"] == 1 and report["intercepts"]["tone_policy"] == 1
    assert any(row["case_id"]=="NG-2026-0843" and "Checklist revision changed" in row["issues"] for row in report["exceptions"])
    assert any(row["case_id"]=="NG-2026-0844" and "QA evidence unavailable" in row["issues"] for row in report["exceptions"])
    assert report["change_control"]["latest_test_passed"] is True and report["change_control"]["latest_test_cases"] == 5
    assert len(report["audit"]) == 4
    assert sum(row["approved"]+row["discarded"] for row in report["daily"]) == 3
    assert "canary" not in json.dumps(report)
    assert "rm@northgate.demo" not in json.dumps(report)
    assert risk_summary(0)["metrics"]["previous_discard_rate"] is None


def test_cro_cannot_authorize_case_reading_oauth():
    from test_mcp_readonly import begin_connection
    client=TestClient(app)
    _,consent=begin_connection(client)
    request_id=re.search(r'name="request_id" value="([^"]+)"',consent.text)[1]
    response=client.post("/oauth/authorize",data={"request_id":request_id,"decision":"allow","email":"cro@northgate.demo","password":"NorthgateDemo!2026"})
    assert response.status_code==400 and response.json()["error"]=="access_denied"
    assert not rows("SELECT * FROM mcp_grants")
    client.close()
