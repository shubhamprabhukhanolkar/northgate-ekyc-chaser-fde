import base64
import hashlib
import re
import time
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from app.main import app
from app.db import connect, rows
from app.mcp.oauth import digest, verify_access

VERIFIER = "a" * 64
RESOURCE = "http://testserver/mcp-readonly/"
REDIRECT = "https://chat.example/callback"


def begin_connection(client, *, scope="northgate:read", redirect=REDIRECT):
    registered = client.post("/oauth/register", json={"client_name": "Test chat", "redirect_uris": [REDIRECT]})
    assert registered.status_code == 201, registered.text
    client_id = registered.json()["client_id"]
    params = {"client_id": client_id, "redirect_uri": redirect, "response_type": "code",
              "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode(),
              "code_challenge_method": "S256", "scope": scope, "state": "test-state", "resource": RESOURCE}
    return client_id, client.get("/oauth/authorize", params=params)


def authorize_code(client, *, signed_in=False):
    client_id, consent = begin_connection(client)
    assert consent.status_code == 200, consent.text
    request_id = re.search(r'name="request_id" value="([^"]+)"', consent.text)[1]
    assert "form-action 'self' https://chat.example" in consent.headers["content-security-policy"]
    assert consent.headers["referrer-policy"] == "same-origin"
    form = {"request_id": request_id, "decision": "allow"}
    if not signed_in:
        form.update(email="rm@northgate.demo", password="NorthgateDemo!2026")
    approved = client.post("/oauth/authorize", data=form, follow_redirects=False)
    assert approved.status_code == 303, approved.text
    query = parse_qs(urlsplit(approved.headers["location"]).query)
    assert query["state"] == ["test-state"]
    return {"client_id": client_id, "code": query["code"][0], "code_verifier": VERIFIER,
            "redirect_uri": REDIRECT, "grant_type": "authorization_code", "resource": RESOURCE}


def connect_user(client, *, signed_in=False):
    form = authorize_code(client, signed_in=signed_in)
    token = client.post("/oauth/token", data=form)
    assert token.status_code == 200, token.text
    return form["client_id"], token.json()


def test_oauth_discovery_validation_and_csrf():
    client = TestClient(app)
    metadata = client.get("/.well-known/oauth-authorization-server").json()
    assert metadata["code_challenge_methods_supported"] == ["S256"]
    assert metadata["scopes_supported"] == ["northgate:read"]
    assert client.get("/.well-known/oauth-protected-resource/mcp-readonly").json()["resource"] == RESOURCE
    denied = client.post("/mcp-readonly/", json={})
    assert denied.status_code == 401 and "resource_metadata" in denied.headers["www-authenticate"]
    for uri in ["https://chat.example/cb#bad", "https://user:pass@chat.example/cb", "http://evil.example/cb", "javascript:alert(1)"]:
        assert client.post("/oauth/register", json={"redirect_uris": [uri]}).status_code == 400
    assert begin_connection(client, scope="northgate:write")[1].status_code == 400
    assert begin_connection(client, redirect="https://evil.example/callback")[1].status_code == 400
    client_id, consent = begin_connection(client)
    request_id = re.search(r'name="request_id" value="([^"]+)"', consent.text)[1]
    client.cookies.clear()
    assert client.post("/oauth/authorize", data={"request_id": request_id, "decision": "allow"}).status_code == 400
    # The shared key and web-login token must not work as read-only MCP tokens.
    session = client.post("/api/auth/login", json={"email": "rm@northgate.demo", "password": "NorthgateDemo!2026"}).json()["access_token"]
    for token in [session, "test-mcp-key"]:
        assert client.post("/mcp-readonly/", headers={"Authorization": f"Bearer {token}"}, json={}).status_code == 401


def test_pkce_code_replay_refresh_and_expiry():
    client = TestClient(app)
    form = authorize_code(client)
    assert client.post("/oauth/token", data={**form, "code_verifier": "b" * 64}).status_code == 400
    assert client.post("/oauth/token", data={**form, "redirect_uri": "https://evil.example"}).status_code == 400
    assert client.post("/oauth/token", data={**form, "resource": "http://testserver/mcp/"}).status_code == 400
    exchanged = client.post("/oauth/token", data=form)
    assert exchanged.status_code == 200, exchanged.text
    token = exchanged.json()
    assert client.post("/oauth/token", data=form).status_code == 400
    identity = verify_access(token["access_token"], RESOURCE)
    assert identity["email"] == "rm@northgate.demo"
    assert verify_access(token["access_token"], "http://testserver/mcp/") is None
    assert not rows("SELECT * FROM mcp_tokens WHERE hash=?", (token["access_token"],))
    refresh = {"grant_type": "refresh_token", "client_id": form["client_id"], "refresh_token": token["refresh_token"], "resource": RESOURCE}
    rotated = client.post("/oauth/token", data=refresh)
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != token["refresh_token"]
    assert client.post("/oauth/token", data=refresh).status_code == 400
    with connect() as db:
        db.execute("UPDATE mcp_tokens SET expires_at=? WHERE hash=?", (time.time()-1, digest(token["access_token"])))
    assert verify_access(token["access_token"], RESOURCE) is None
    assert client.post("/oauth/revoke", data={"token": rotated.json()["refresh_token"], "client_id": form["client_id"]}).status_code == 200
    assert verify_access(rotated.json()["access_token"], RESOURCE) is None


def test_connection_ownership_and_disconnect():
    client = TestClient(app)
    assert client.get("/api/mcp/connections").status_code == 401
    client.post("/api/auth/login", json={"email": "rm@northgate.demo", "password": "NorthgateDemo!2026"})
    _, token = connect_user(client, signed_in=True)
    grant = client.get("/api/mcp/connections").json()["connections"][0]
    assert "token" not in str(grant)
    client.post("/api/auth/login", json={"email": "analyst@northgate.demo", "password": "NorthgateDemo!2026"})
    assert client.get("/api/mcp/connections").json()["connections"] == []
    assert client.delete("/api/mcp/connections/" + grant["id"]).status_code == 404
    client.post("/api/auth/login", json={"email": "rm@northgate.demo", "password": "NorthgateDemo!2026"})
    assert client.delete("/api/mcp/connections/" + grant["id"]).status_code == 200
    assert verify_access(token["access_token"], RESOURCE) is None
    assert client.get("/api/mcp/connections").json()["connections"] == []


def test_cancel_expired_consent_and_expired_grant():
    client = TestClient(app)
    _, consent = begin_connection(client)
    request_id = re.search(r'name="request_id" value="([^"]+)"', consent.text)[1]
    denied = client.post("/oauth/authorize", data={"request_id": request_id, "decision": "deny"}, follow_redirects=False)
    assert denied.status_code == 303
    assert parse_qs(urlsplit(denied.headers["location"]).query)["error"] == ["access_denied"]
    assert not rows("SELECT * FROM mcp_codes")
    _, consent = begin_connection(client)
    request_id = re.search(r'name="request_id" value="([^"]+)"', consent.text)[1]
    with connect() as db:
        db.execute("UPDATE mcp_authorizations SET expires_at=?", (time.time()-1,))
    assert client.post("/oauth/authorize", data={"request_id": request_id, "decision": "allow"}).status_code == 400
    client_id, token = connect_user(client)
    with connect() as db:
        db.execute("UPDATE mcp_grants SET expires_at=?", (time.time()-1,))
    assert verify_access(token["access_token"], RESOURCE) is None
    assert client.post("/oauth/token", data={"grant_type": "refresh_token", "client_id": client_id, "refresh_token": token["refresh_token"]}).status_code == 400


def assert_readonly_http(client):
    """Run inside the existing HTTP MCP lifespan test (session managers are single-use)."""
    _, tokens = connect_user(client)
    headers = {"Authorization": "Bearer " + tokens["access_token"], "Accept": "application/json, text/event-stream"}
    def rpc(method, params):
        response = client.post("/mcp-readonly/", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        assert response.status_code == 200, response.text
        return response.json()
    initialized = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "1"}})
    assert initialized["result"]["serverInfo"]["name"] == "Northgate read-only cases"
    tools = rpc("tools/list", {})["result"]["tools"]
    assert {t["name"] for t in tools} == {"list_onboarding_cases", "get_case_gap_checklist", "get_case_draft"}
    assert all(t["annotations"]["readOnlyHint"] for t in tools)
    result = rpc("tools/call", {"name": "list_onboarding_cases", "arguments": {"jurisdiction": "SG"}})
    assert not result["result"].get("isError"), result
    assert len(result["result"]["structuredContent"]["cases"]) == 14
    for name in ["get_case_gap_checklist", "get_case_draft"]:
        result = rpc("tools/call", {"name": name, "arguments": {"case_id": "NG-2026-0841"}})
        assert not result["result"].get("isError"), result
    assert not rows("SELECT * FROM read_receipts")
    for name in ["generate_chase_draft", "approve_or_discard_draft", "update_toner_settings"]:
        result = rpc("tools/call", {"name": name, "arguments": {"case_id": "NG-2026-0841", "action": "discard"}})
        assert result.get("error") or result["result"].get("isError"), result
    assert client.post("/mcp/", headers=headers, json={}).status_code == 401
    assert client.get("/api/cases", headers=headers).status_code == 401
    assert client.post("/api/cases/NG-2026-0841/generate", headers=headers).status_code == 401
    assert not rows("SELECT * FROM drafts")
    assert not rows("SELECT * FROM outbox")
    assert rows("SELECT * FROM audit WHERE action='mcp_readonly_case_checklist'")[0]["actor"] == "rm@northgate.demo"
