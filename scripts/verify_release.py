"""Verify a deployed release using synthetic cases. Never approves or sends a draft."""
import json
import sys
from pathlib import Path
import httpx
from dotenv import dotenv_values

values = dotenv_values(Path(__file__).resolve().parents[1]/".env")
base = sys.argv[1].rstrip("/") if len(sys.argv)>1 else "http://127.0.0.1:8080"


def login(client, role):
    response = client.post("/api/auth/login", json={"email":f"{role}@northgate.demo", "password":values.get("DEFAULT_OPERATOR_PASSWORD") or "NorthgateDemo!2026"})
    response.raise_for_status()


def workflow(client, case_id, mode, instructions):
    client.get(f"/api/cases/{case_id}").raise_for_status()
    response = client.post(f"/api/cases/{case_id}/runs", json={"mode":mode,"instructions":instructions})
    response.raise_for_status()
    run_id = response.json()["id"]
    events = []
    with client.stream("GET",f"/api/runs/{run_id}/events") as stream:
        stream.raise_for_status()
        for line in stream.iter_lines():
            if line.startswith("data: "):
                event=json.loads(line[6:])
                events.append(event)
                if event["kind"] == "run_failed":
                    raise RuntimeError(event["data"]["summary"])
    assert events[-1]["kind"] == "run_completed"
    assert events[-1]["data"]["draft"]["status"] == "REVIEW", events[-1]["data"]["draft"]["scorecard"]
    assert {event["data"]["node"] for event in events if event["kind"] == "node_started"} == {"deterministic","orchestrator","drafter","toner","critique"}
    assert {event["data"]["agent"] for event in events if event["kind"] == "draft_preview"} == {"drafter","toner"}
    cursor=events[-2]["id"]
    replay=client.get(f"/api/runs/{run_id}/events",headers={"Last-Event-ID":str(cursor)})
    replay.raise_for_status()
    assert all(json.loads(line[6:])["id"]>cursor for line in replay.text.splitlines() if line.startswith("data: "))
    print(f"Verified {mode} drafting, both provider previews, QA and SSE resume: {case_id}",flush=True)
    return events


with httpx.Client(base_url=base,timeout=180,follow_redirects=True) as client:
    health=client.get("/api/health")
    health.raise_for_status()
    assert not health.json()["offline_demo"]
    client.get("/").raise_for_status()
    login(client,"rm")
    cases=client.get("/api/cases").json()
    assert len(cases)==42 and all(case["contact"].endswith("@example.com") for case in cases)
    events=workflow(client,"NG-2026-0843","guided","Keep the email warm and concise. Use bullet points for every outstanding document and offer help.")
    response=client.post("/api/policy/query",json={"question":"Where do I change Auto-draft to Guided draft, and where do I put redraft guidance?"})
    response.raise_for_status()
    assert any(c["id"].startswith("NG-PORTAL-") for c in response.json()["citations"])
    traces=client.get("/api/traces").json()
    assert {"deterministic","orchestrator","drafter","toner","critique","policy_copilot"}.issubset({trace["node"] for trace in traces})
    print("Verified 42 synthetic cases, portal-use guidance and traces for all six agents",flush=True)
    headers={"Authorization":"Bearer "+values["MCP_API_KEY"],"Accept":"application/json, text/event-stream"}
    payload={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"release-verification","version":"1"}}}
    response=client.post("/mcp/",headers=headers,json=payload)
    response.raise_for_status()
    assert response.json()["result"]["serverInfo"]["name"]=="Northgate eKYC"
    response=client.post("/mcp/",headers=headers,json={"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_finops_cost_summary","arguments":{}}})
    response.raise_for_status()
    assert not response.json()["result"].get("isError")
    print("Verified authenticated MCP and cost telemetry",flush=True)
    if "--failover" in sys.argv:
        login(client,"admin")
        prior=client.get("/api/runtime").json()["simulate_outage"]
        client.put("/api/runtime/outage",json={"enabled":True}).raise_for_status()
        try:
            backup=workflow(client,"NG-2026-0842","auto","Use a polite concise request and offer assistance.")
            assert any(e["kind"]=="provider_failover" for e in backup)
            assert all(e["data"]["provider"]=="groq" for e in backup if e["kind"]=="draft_preview")
            print("Verified real Groq streaming failover with optional auto-redraft guidance",flush=True)
        finally:
            client.put("/api/runtime/outage",json={"enabled":prior}).raise_for_status()
            print("Original provider routing restored",flush=True)
print("Release verification passed. Drafts remain pending human review; no sends approved.",flush=True)
