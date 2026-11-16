"""Official FastMCP adapter. Run from backend: uv run --project .. python -m app.mcp.server."""
import json
from contextlib import asynccontextmanager
from typing import Literal, Any
import jwt
from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from ..config import settings
from ..db import initialize, prompt, connect, audit, now
from ..agents.deterministic import gap_check
from ..agents.copilot import query
from ..routes.prompts_routes import ToneSettings
from .. import services


@asynccontextmanager
async def lifespan(server):
    initialize()
    yield {}


mcp = FastMCP("Northgate eKYC", instructions="Synthetic banking prototype. Read the case checklist before writes. Drafts never auto-send. Approvals require an RM-issued short-lived token; direct agents cannot authorize sends.",
    lifespan=lifespan, stateless_http=True, json_response=True, streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
        allowed_hosts=["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*", "testserver"] + [h.strip() for h in settings().mcp_allowed_hosts.split(",") if h.strip()],
        allowed_origins=["http://localhost", "http://localhost:*", "http://127.0.0.1", "http://127.0.0.1:*"] + ["https://"+h.strip() for h in settings().mcp_allowed_hosts.split(",") if h.strip()]))
MCP_ACTOR = "mcp:integration"


@mcp.tool()
def list_onboarding_cases(jurisdiction: str | None = None, status: str | None = None) -> dict[str, Any]:
    """List synthetic onboarding cases and nudge flags. Does not authorize mutations."""
    return {"cases": services.list_cases(jurisdiction, status), "synthetic": True}


@mcp.tool()
def get_case_gap_checklist(case_id: str) -> dict[str, Any]:
    """Read the authoritative received/locked and missing checklist before generating a draft."""
    return gap_check(case_id, MCP_ACTOR)


@mcp.tool()
async def generate_chase_draft(case_id: str) -> dict[str, Any]:
    """Run all five LangGraph nodes, including cyclical critique. Requires a current checklist read. Never sends."""
    return await services.generate(case_id, MCP_ACTOR)


@mcp.tool()
def approve_or_discard_draft(case_id: str, action: Literal["approve_send", "discard"], reason: str | None = None, rm_approval_token: str | None = None) -> dict[str, Any]:
    """Discard a reviewed draft or record an RM-approved synthetic send. For approve_send obtain a token from an RM who explicitly reviews and authorizes the exact draft in the UI. Shared MCP credentials alone cannot approve."""
    if action == "discard":
        return services.decision(case_id, MCP_ACTOR, action, reason)
    if not rm_approval_token:
        return {"requires_human_approval": True, "review_path": f"/?case={case_id}", "message": "RM must review the draft and issue a two-minute approval token from the workspace."}
    try:
        claims = jwt.decode(rm_approval_token, settings().auth_secret, algorithms=["HS256"])
        draft = services.get_draft(case_id)
        if claims.get("purpose") != "mcp_approve" or claims.get("case_id") != case_id or not draft or claims.get("digest") != services.prompt_digest({"subject": draft["subject"], "body": draft["body"]}):
            raise ValueError("Token does not match this draft")
        return services.decision(case_id, claims["sub"], action, reason, claims["draft_id"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise ValueError("Invalid or expired RM approval token") from exc


@mcp.tool()
def get_finops_cost_summary() -> dict[str, Any]:
    """Read measured provider usage, failovers, RM discard rate and projected ROI."""
    return services.finops()


@mcp.tool()
async def query_kyc_policy(question: str) -> dict[str, Any]:
    """Answer with citations to synthetic Northgate policy only."""
    if not 3 <= len(question) <= 3000:
        raise ValueError("Question must be 3–3000 characters")
    return await query(question)


@mcp.tool()
async def update_toner_settings(formality: int, urgency: str, jurisdiction_clause: str) -> dict[str, Any]:
    """Validate controls, run the mandatory five-case regression, and persist a version only on a passing result."""
    controls = ToneSettings(formality=formality, urgency=urgency, jurisdiction_clause=jurisdiction_clause).model_dump()
    candidate = {"toner": {"content": prompt("toner")["content"], "settings": controls}}
    result = await services.regression(candidate)
    if not result["passed"]:
        return {"saved": False, "regression": result}
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute("SELECT * FROM prompt_versions WHERE agent='toner' ORDER BY version DESC LIMIT 1").fetchone()
        db.execute("INSERT INTO prompt_versions(agent,content,settings,version,created_at,actor) VALUES(?,?,?,?,?,?)", ("toner", current["content"], json.dumps(controls), current["version"]+1, now(), MCP_ACTOR))
        audit(db, MCP_ACTOR, "toner_settings_updated", payload={"settings": controls, "regression_id": result["id"]})
    return {"saved": True, "settings": controls, "regression": result}


if __name__ == "__main__":
    mcp.run(transport="stdio")
