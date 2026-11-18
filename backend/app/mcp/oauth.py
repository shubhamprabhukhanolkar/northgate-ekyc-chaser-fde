"""User-delegated, read-only MCP access. Tokens are opaque and stored hashed."""
import base64
import hashlib
import html
import json
import re
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, ValidationError

from ..auth import current_user
from ..config import settings
from ..db import audit, connect, now, rows
from ..routes.auth_routes import Login, login

router = APIRouter(tags=["MCP account linking"])
SCOPE = "northgate:read"
READONLY_PATH = "/mcp-readonly/"
ACCESS_SECONDS = 3600
GRANT_SECONDS = 30 * 86400


class OAuthError(Exception):
    def __init__(self, error, description, status=400):
        self.error, self.description, self.status = error, description, status


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def origin(request):
    configured = settings().public_base_url.rstrip("/")
    value = configured or str(request.base_url).rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise HTTPException(503, "Configure PUBLIC_BASE_URL as the portal origin")
    local = parsed.hostname in ("localhost", "127.0.0.1", "::1", "testserver")
    allowed = [h.strip() for h in settings().mcp_allowed_hosts.split(",") if h.strip()]
    if not configured and not local and parsed.netloc not in allowed:
        raise HTTPException(503, "Configure PUBLIC_BASE_URL for account linking")
    if parsed.scheme != "https" and not local:
        raise HTTPException(503, "Account linking requires HTTPS")
    return value


def resource_url(request):
    return origin(request) + READONLY_PATH


def security_headers():
    return {"Cache-Control": "no-store", "Pragma": "no-cache", "Referrer-Policy": "same-origin",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"}


@router.get("/.well-known/oauth-authorization-server")
def authorization_metadata(request: Request):
    base = origin(request)
    return {"issuer": base, "authorization_endpoint": base + "/oauth/authorize",
            "token_endpoint": base + "/oauth/token", "registration_endpoint": base + "/oauth/register",
            "revocation_endpoint": base + "/oauth/revoke", "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"], "scopes_supported": [SCOPE],
            "token_endpoint_auth_methods_supported": ["none"], "code_challenge_methods_supported": ["S256"]}


@router.get("/.well-known/oauth-protected-resource/mcp-readonly")
@router.get("/.well-known/oauth-protected-resource/mcp-readonly/")
def resource_metadata(request: Request):
    return {"resource": resource_url(request), "authorization_servers": [origin(request)],
            "scopes_supported": [SCOPE], "bearer_methods_supported": ["header"],
            "resource_name": "Northgate read-only cases"}


class Registration(BaseModel):
    client_name: str = Field(default="MCP client", min_length=1, max_length=100)
    redirect_uris: list[str] = Field(min_length=1, max_length=10)
    token_endpoint_auth_method: str = "none"
    grant_types: list[str] = Field(default=["authorization_code", "refresh_token"], max_length=2)
    response_types: list[str] = Field(default=["code"], max_length=1)


def valid_redirect(uri):
    try:
        u = urlsplit(uri)
        u.port  # Reject malformed ports as well as malformed host syntax.
        return (len(uri) <= 2048 and not any(ord(c) < 33 for c in uri) and "#" not in uri
                and not u.username and not u.password and bool(u.hostname) and bool(u.netloc)
                and re.fullmatch(r"[A-Za-z0-9.:\-]+", u.hostname) is not None
                and (u.scheme == "https" or (u.scheme == "http" and u.hostname in ("127.0.0.1", "::1", "localhost"))))
    except ValueError:
        return False


@router.post("/oauth/register", status_code=201)
def register(body: Registration, request: Request):
    origin(request)
    if not all(valid_redirect(u) for u in body.redirect_uris):
        raise OAuthError("invalid_redirect_uri", "Use exact HTTPS redirects or loopback HTTP redirects")
    if body.token_endpoint_auth_method != "none" or body.response_types != ["code"] or not set(body.grant_types) <= {"authorization_code", "refresh_token"}:
        raise OAuthError("invalid_client_metadata", "Only public PKCE authorization-code clients are supported")
    client_id = secrets.token_urlsafe(24)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        # Bound unauthenticated registration growth without relying on spoofable forwarding headers.
        recent = db.execute("SELECT count(*) FROM mcp_clients WHERE created_at > datetime('now', '-1 day')").fetchone()[0]
        if recent >= 1000:
            raise OAuthError("temporarily_unavailable", "Client registration capacity reached", 429)
        db.execute("INSERT INTO mcp_clients VALUES(?,?,?,?)", (client_id, body.client_name, json.dumps(body.redirect_uris), now()))
    return {"client_id": client_id, "client_name": body.client_name, "redirect_uris": body.redirect_uris,
            "token_endpoint_auth_method": "none", "grant_types": body.grant_types, "response_types": ["code"]}


def find_client(client_id):
    found = rows("SELECT * FROM mcp_clients WHERE id=?", (client_id,))
    if not found:
        raise OAuthError("invalid_client", "Unknown client")
    return found[0]


def logged_in(request):
    try:
        return current_user(request)
    except HTTPException:
        return None


@router.get("/oauth/authorize", response_class=HTMLResponse)
def authorize(request: Request, client_id: str, redirect_uri: str, code_challenge: str,
              response_type: str = "code", code_challenge_method: str = "S256", scope: str = SCOPE,
              state: str = "", resource: str | None = None):
    client = find_client(client_id)
    if redirect_uri not in json.loads(client["redirects"]):
        raise OAuthError("invalid_request", "Redirect URI does not match registration")
    if response_type != "code" or code_challenge_method != "S256" or not re.fullmatch(r"[A-Za-z0-9_-]{43}", code_challenge):
        raise OAuthError("invalid_request", "Authorization code with S256 PKCE is required")
    if scope != SCOPE:
        raise OAuthError("invalid_scope", "Only northgate:read is available")
    audience = resource_url(request)
    if resource is not None and resource != audience:
        raise OAuthError("invalid_target", "Resource must be the read-only MCP URL")
    if len(state) > 2048:
        raise OAuthError("invalid_request", "State is too long")
    pending, csrf = secrets.token_urlsafe(24), secrets.token_urlsafe(32)
    with connect() as db:
        db.execute("DELETE FROM mcp_authorizations WHERE expires_at < ?", (time.time(),))
        if db.execute("SELECT count(*) FROM mcp_authorizations").fetchone()[0] >= 1000:
            raise OAuthError("temporarily_unavailable", "Please try account linking later", 429)
        db.execute("INSERT INTO mcp_authorizations VALUES(?,?,?,?,?,?,?,?)", (pending, client_id, redirect_uri,
                   code_challenge, state, audience, digest(csrf), time.time()+600))
    user = logged_in(request)
    identity = (f'<p>Signed in as <strong>{html.escape(user["email"])}</strong></p>' if user else
                '<label>Email<input name="email" type="email" autocomplete="username" maxlength="200" required></label>'
                '<label>Password<input name="password" type="password" autocomplete="current-password" maxlength="300" required></label>')
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Connect Northgate read-only</title><style>
    body{{font:16px system-ui;background:#102126;color:#eaf3ef;margin:0;padding:32px 16px}}main{{max-width:480px;margin:5vh auto;background:#193139;padding:32px;border-radius:20px;border:1px solid #42605d}}
    h1{{font-size:26px}}p,li{{line-height:1.6}}label{{display:block;margin:16px 0}}input{{display:block;box-sizing:border-box;width:100%;padding:12px;margin-top:6px;border-radius:8px;border:1px solid #6e8c86}}
    button{{padding:12px 18px;border:0;border-radius:9px;cursor:pointer;margin:6px 8px 0 0;background:#9ee6b5;color:#102126;font-weight:700}}button[value=deny]{{background:#d8dedc}}
    small{{color:#c0d1cb}}strong{{overflow-wrap:anywhere}}</style><main><small>NORTHGATE · ACCOUNT CONNECTION</small>
    <h1>Allow read-only access?</h1><p><strong>{html.escape(client["name"])}</strong> wants to read the portal's shared synthetic case queue, document checklists and existing drafts.</p>
    <p>It cannot draft, edit, approve, send, or change settings. The portal currently shares the same case queue across operators.</p>
    <small>Client ID: {html.escape(client_id)}<br>Returns to: {html.escape(redirect_uri)}<br>Connection expires after 30 days. You can disconnect it in the portal.</small>
    <form method="post" action="/oauth/authorize"><input type="hidden" name="request_id" value="{pending}">{identity}
    <button name="decision" value="allow">Allow read-only access</button><button name="decision" value="deny" formnovalidate>Cancel</button></form></main></html>'''
    headers = security_headers()
    target = urlsplit(redirect_uri)
    # Chromium checks form-action against the final OAuth redirect as well as the POST.
    headers["Content-Security-Policy"] = headers["Content-Security-Policy"].replace("form-action 'self'", f"form-action 'self' {target.scheme}://{target.netloc}")
    response = HTMLResponse(page, headers=headers)
    response.set_cookie("northgate_mcp_consent", csrf, httponly=True, secure=settings().secure_cookies or origin(request).startswith("https:"), samesite="lax", max_age=600, path="/oauth/authorize")
    return response


async def form_body(request):
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/x-www-form-urlencoded":
        raise OAuthError("invalid_request", "Expected form-encoded request")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 16384:
            raise OAuthError("invalid_request", "Request is too large", 413)
    try:
        parsed = parse_qs(raw.decode(), keep_blank_values=True, max_num_fields=25)
    except (ValueError, UnicodeDecodeError):
        raise OAuthError("invalid_request", "Invalid form")
    if any(len(v) != 1 for v in parsed.values()):
        raise OAuthError("invalid_request", "Duplicate parameters are not allowed")
    return {k: v[0] for k, v in parsed.items()}


@router.post("/oauth/authorize")
async def consent(request: Request):
    data = await form_body(request)
    pending = rows("SELECT * FROM mcp_authorizations WHERE id=?", (data.get("request_id", ""),))
    if not pending or pending[0]["expires_at"] <= time.time() or not secrets.compare_digest(pending[0]["csrf_hash"], digest(request.cookies.get("northgate_mcp_consent", ""))):
        raise OAuthError("invalid_request", "Consent expired or browser verification failed; reconnect")
    pending = pending[0]
    allowed = data.get("decision") == "allow"
    user = logged_in(request)
    if allowed and not user:
        # Reuse the portal's password verification and login throttling.
        try:
            credentials = Login(email=data.get("email", ""), password=data.get("password", ""))
        except ValidationError:
            raise OAuthError("invalid_request", "Invalid sign-in fields")
        user = login(credentials, Response(), request)["user"]
    if allowed and user["role"] in ("cfo", "cro"):
        raise OAuthError("access_denied", "Executive accounts are limited to their read-only dashboard")
    code = secrets.token_urlsafe(32)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("DELETE FROM mcp_authorizations WHERE id=? AND expires_at>?", (pending["id"], time.time())).rowcount != 1:
            raise OAuthError("invalid_request", "Consent already used or expired")
        if allowed:
            db.execute("INSERT INTO mcp_codes VALUES(?,?,?,?,?,?,?)", (digest(code), pending["client_id"], user["email"], pending["redirect_uri"], pending["challenge"], pending["resource"], time.time()+120))
            audit(db, user["email"], "mcp_readonly_consent", payload={"client_id": pending["client_id"]})
    params = {"code": code} if allowed else {"error": "access_denied"}
    params["state"] = pending["state"]
    response = RedirectResponse(pending["redirect_uri"] + ("&" if "?" in pending["redirect_uri"] else "?") + urlencode(params), status_code=303, headers=security_headers())
    response.delete_cookie("northgate_mcp_consent", path="/oauth/authorize")
    return response


def issue_tokens(db, grant_id):
    access, refresh = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
    grant = db.execute("SELECT * FROM mcp_grants WHERE id=?", (grant_id,)).fetchone()
    access_lifetime = min(ACCESS_SECONDS, int(grant["expires_at"] - time.time()))
    db.execute("INSERT INTO mcp_tokens VALUES(?,?,?,?)", (digest(access), grant_id, "access", time.time()+access_lifetime))
    db.execute("INSERT INTO mcp_tokens VALUES(?,?,?,?)", (digest(refresh), grant_id, "refresh", grant["expires_at"]))
    return JSONResponse({"access_token": access, "token_type": "Bearer", "expires_in": access_lifetime,
                         "refresh_token": refresh, "scope": SCOPE}, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


@router.post("/oauth/token")
async def exchange(request: Request):
    data = await form_body(request)
    client_id = data.get("client_id", "")
    find_client(client_id)
    audience = resource_url(request)
    if data.get("resource", audience) != audience:
        raise OAuthError("invalid_target", "Wrong resource")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if data.get("grant_type") == "authorization_code":
            code_hash = digest(data.get("code", ""))
            code = db.execute("SELECT * FROM mcp_codes WHERE hash=?", (code_hash,)).fetchone()
            verifier = data.get("code_verifier", "")
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            if not code or code["expires_at"] <= time.time() or code["client_id"] != client_id or code["redirect_uri"] != data.get("redirect_uri") or code["resource"] != audience or not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", verifier) or not secrets.compare_digest(code["challenge"], challenge):
                raise OAuthError("invalid_grant", "Invalid, expired or mismatched authorization code")
            db.execute("DELETE FROM mcp_codes WHERE hash=?", (code_hash,))
            grant_id = secrets.token_urlsafe(24)
            db.execute("INSERT INTO mcp_grants VALUES(?,?,?,?,?,?,0)", (grant_id, client_id, code["email"], audience, now(), time.time()+GRANT_SECONDS))
            audit(db, code["email"], "mcp_readonly_connected", payload={"grant_id": grant_id, "client_id": client_id})
            return issue_tokens(db, grant_id)
        if data.get("grant_type") == "refresh_token":
            token_hash = digest(data.get("refresh_token", ""))
            grant = db.execute("SELECT g.* FROM mcp_tokens t JOIN mcp_grants g ON g.id=t.grant_id JOIN users u ON u.email=g.email WHERE t.hash=? AND t.kind='refresh' AND t.expires_at>? AND g.expires_at>? AND g.revoked=0 AND g.client_id=? AND g.resource=?", (token_hash, time.time(), time.time(), client_id, audience)).fetchone()
            if not grant or data.get("scope", SCOPE) != SCOPE:
                raise OAuthError("invalid_grant", "Connection expired or revoked")
            # Rotation: a refresh token can be exchanged only once.
            db.execute("DELETE FROM mcp_tokens WHERE hash=?", (token_hash,))
            return issue_tokens(db, grant["id"])
    raise OAuthError("unsupported_grant_type", "Use authorization_code or refresh_token")


def verify_access(token, resource):
    if not token or len(token) > 512:
        return None
    found = rows("SELECT g.id AS grant_id,g.email,u.role FROM mcp_tokens t JOIN mcp_grants g ON g.id=t.grant_id JOIN users u ON u.email=g.email WHERE t.hash=? AND t.kind='access' AND t.expires_at>? AND g.expires_at>? AND g.revoked=0 AND g.resource=?", (digest(token), time.time(), time.time(), resource))
    return found[0] if found else None


@router.post("/oauth/revoke")
async def revoke(request: Request):
    data = await form_body(request)
    with connect() as db:
        grant = db.execute("SELECT g.* FROM mcp_tokens t JOIN mcp_grants g ON g.id=t.grant_id WHERE t.hash=? AND g.client_id=?", (digest(data.get("token", "")), data.get("client_id", ""))).fetchone()
        if grant:
            db.execute("UPDATE mcp_grants SET revoked=1 WHERE id=?", (grant["id"],))
            audit(db, grant["email"], "mcp_readonly_disconnected", payload={"grant_id": grant["id"]})
    return Response(status_code=200, headers={"Cache-Control": "no-store"})


@router.get("/api/mcp/connections")
def connections(request: Request, user=Depends(current_user)):
    return {"endpoint": resource_url(request), "scope": SCOPE, "shared_queue": True,
            "connections": rows("SELECT g.id,c.name AS client_name,g.created_at,g.expires_at FROM mcp_grants g JOIN mcp_clients c ON c.id=g.client_id WHERE g.email=? AND g.revoked=0 AND g.expires_at>? ORDER BY g.created_at DESC", (user["email"], time.time()))}


@router.delete("/api/mcp/connections/{grant_id}")
def disconnect(grant_id: str, user=Depends(current_user)):
    with connect() as db:
        if not db.execute("UPDATE mcp_grants SET revoked=1 WHERE id=? AND email=? AND revoked=0", (grant_id, user["email"])).rowcount:
            raise HTTPException(404, "Connection not found")
        audit(db, user["email"], "mcp_readonly_disconnected", payload={"grant_id": grant_id})
    return {"ok": True}
