"""Exercise deployed user-delegated MCP without generating or modifying any case."""
import base64
import hashlib
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
from dotenv import dotenv_values

base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8080"
values = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
with httpx.Client(base_url=base, timeout=60) as portal:
    meta = portal.get("/.well-known/oauth-protected-resource/mcp-readonly")
    meta.raise_for_status()
    resource = meta.json()["resource"]
    # Follow the advertised canonical origin for audience and session consistency.
    canonical = resource.removesuffix("/mcp-readonly/")
    portal.base_url = httpx.URL(canonical)
    login = portal.post("/api/auth/login", json={"email": "rm@northgate.demo", "password": values.get("DEFAULT_OPERATOR_PASSWORD") or "NorthgateDemo!2026"})
    login.raise_for_status()
    existing = {c["id"] for c in portal.get("/api/mcp/connections").json()["connections"]}
    callback = "https://example.com/northgate-mcp-release-check"
    name = "Northgate release verification " + secrets.token_hex(4)
    registered = portal.post("/oauth/register", json={"client_name": name, "redirect_uris": [callback]})
    registered.raise_for_status()
    client_id = registered.json()["client_id"]
    verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(24)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    consent = portal.get("/oauth/authorize", params={"client_id": client_id, "redirect_uri": callback,
        "response_type": "code", "code_challenge": challenge, "code_challenge_method": "S256", "scope": "northgate:read", "state": state, "resource": resource})
    consent.raise_for_status()
    request_id = re.search(r'name="request_id" value="([^"]+)"', consent.text)[1]
    approved = portal.post("/oauth/authorize", data={"request_id": request_id, "decision": "allow"})
    assert approved.status_code == 303
    params = parse_qs(urlsplit(approved.headers["location"]).query)
    assert params["state"] == [state]
    with httpx.Client(base_url=canonical, timeout=60) as reader:
        exchanged = reader.post("/oauth/token", data={"grant_type": "authorization_code", "client_id": client_id,
            "code": params["code"][0], "code_verifier": verifier, "redirect_uri": callback, "resource": resource})
        exchanged.raise_for_status()
        tokens = exchanged.json()
        grants = portal.get("/api/mcp/connections").json()["connections"]
        grant = next(g for g in grants if g["id"] not in existing and g["client_name"] == name)
        headers = {"Authorization": "Bearer " + tokens["access_token"], "Accept": "application/json, text/event-stream"}
        def rpc(method, params):
            response = reader.post("/mcp-readonly/", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
            response.raise_for_status()
            return response.json()
        try:
            result = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "release-check", "version": "1"}})
            assert result["result"]["serverInfo"]["name"] == "Northgate read-only cases"
            tools = rpc("tools/list", {})["result"]["tools"]
            assert {t["name"] for t in tools} == {"list_onboarding_cases", "get_case_gap_checklist", "get_case_draft"}
            result = rpc("tools/call", {"name": "list_onboarding_cases", "arguments": {}})["result"]
            assert not result.get("isError")
            cases = result["structuredContent"]["cases"]
            assert len(cases) == 42
            for tool in ["get_case_gap_checklist", "get_case_draft"]:
                assert not rpc("tools/call", {"name": tool, "arguments": {"case_id": cases[0]["id"]}})["result"].get("isError")
            denied = rpc("tools/call", {"name": "generate_chase_draft", "arguments": {"case_id": cases[0]["id"]}})
            assert denied.get("error") or denied["result"].get("isError")
            assert reader.post("/mcp/", headers=headers, json={}).status_code == 401
            assert reader.get("/api/cases", headers=headers).status_code == 401
            assert reader.post(f'/api/cases/{cases[0]["id"]}/generate', headers=headers).status_code == 401
            refreshed = reader.post("/oauth/token", data={"grant_type": "refresh_token", "client_id": client_id, "refresh_token": tokens["refresh_token"], "resource": resource})
            refreshed.raise_for_status()
            refreshed_access = refreshed.json()["access_token"]
        finally:
            portal.delete("/api/mcp/connections/" + grant["id"]).raise_for_status()
        assert reader.post("/mcp-readonly/", headers=headers, json={}).status_code == 401
        assert reader.post("/mcp-readonly/", headers={**headers, "Authorization": "Bearer " + refreshed_access}, json={}).status_code == 401
print("Verified user consent, 42 cases, 3 read-only tools, blocked writes, refresh and revocation. Verification connection disconnected; no cases changed.")
