"""Exercise the running app with real keys. Prints only safety and usage summaries."""
import json
import sys
from pathlib import Path
import httpx
from dotenv import dotenv_values

base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
values = dotenv_values(Path(__file__).resolve().parents[1]/".env")
with httpx.Client(base_url=base, timeout=180, follow_redirects=True) as client:
    r = client.get("/api/health")
    r.raise_for_status()
    print("Health:", r.json(), flush=True)
    assert client.get("/").status_code == 200
    r = client.post("/api/auth/login", json={"email": "rm@northgate.demo", "password": values.get("DEFAULT_OPERATOR_PASSWORD", "NorthgateDemo!2026")})
    r.raise_for_status()
    cases = client.get("/api/cases").json()
    cid = cases[0]["id"]
    client.get(f"/api/cases/{cid}").raise_for_status()
    r = client.post(f"/api/cases/{cid}/generate")
    r.raise_for_status()
    d = r.json()
    print("Live draft:", {"status": d["status"], "provider": d["provider"], "scorecard": d["scorecard"]}, flush=True)
    assert d["scorecard"]["passed"] and d["status"] == "REVIEW"
    r = client.post("/api/policy/query", json={"question": "When is a nudge due and who approves it?"})
    r.raise_for_status()
    assert r.json()["citations"]
    print("Policy citations:", [c["id"] for c in r.json()["citations"]], flush=True)
    costs = client.get("/api/finops").json()
    assert {"orchestrator", "drafter", "toner", "critique", "policy_copilot"}.issubset({a["agent_name"] for a in costs["agents"]})
    print("Recorded agent calls:", costs["calls"], "cost USD:", costs["cost_usd"], flush=True)
    headers = {"Authorization": "Bearer " + values["MCP_API_KEY"], "Accept": "application/json, text/event-stream"}
    initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "1"}}}
    r = client.post("/mcp/", headers=headers, json=initialize)
    r.raise_for_status()
    assert r.json()["result"]["serverInfo"]["name"] == "Northgate eKYC"
    for name, args in (("list_onboarding_cases", {}), ("get_case_gap_checklist", {"case_id": cid}), ("get_finops_cost_summary", {})):
        r = client.post("/mcp/", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": args}})
        r.raise_for_status()
        assert not r.json()["result"].get("isError"), r.text
        assert "structuredContent" in r.json()["result"]
        print("MCP verified:", name, flush=True)
    print("Live smoke verification passed; generated draft remains pending RM review.", flush=True)
