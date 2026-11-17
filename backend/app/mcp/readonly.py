"""Separate tool registry: user connections cannot discover or invoke write tools."""
from typing import Any
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from .. import services
from ..agents.deterministic import gap_check
from ..db import audit, connect
from .server import mcp as integration_mcp

readonly_mcp = FastMCP(
    "Northgate read-only cases", stateless_http=True, json_response=True,
    streamable_http_path="/", transport_security=integration_mcp.settings.transport_security,
    instructions="Read-only access to the Northgate portal's shared synthetic case queue. "
    "You can list cases, inspect missing/received documents and read existing drafts. "
    "You cannot generate, edit, approve, discard, send, or change settings. Cases are not individually assigned."
)
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


def record_read(ctx, action, case_id=None):
    request = ctx.request_context.request
    identity = getattr(getattr(request, "state", None), "mcp_reader", None)
    if not identity:
        raise ValueError("An authenticated read-only user connection is required")
    with connect() as db:
        audit(db, identity["email"], action, case_id, {"grant_id": identity["grant_id"], "scope": "northgate:read"})


@readonly_mcp.tool(annotations=READ_ONLY)
def list_onboarding_cases(ctx: Context, jurisdiction: str | None = None, status: str | None = None) -> dict[str, Any]:
    """List the same shared synthetic case queue available in the portal, with follow-up flags."""
    record_read(ctx, "mcp_readonly_list_cases")
    return {"cases": services.list_cases(jurisdiction, status), "synthetic": True, "shared_queue": True}


@readonly_mcp.tool(annotations=READ_ONLY)
def get_case_gap_checklist(case_id: str, ctx: Context) -> dict[str, Any]:
    """Read a case's received and missing documents, status, contact and follow-up details."""
    record_read(ctx, "mcp_readonly_case_checklist", case_id)
    return gap_check(case_id)


@readonly_mcp.tool(annotations=READ_ONLY)
def get_case_draft(case_id: str, ctx: Context) -> dict[str, Any]:
    """Read the latest existing draft and review scorecard. Never generates or changes a draft."""
    record_read(ctx, "mcp_readonly_case_draft", case_id)
    gap_check(case_id)
    return {"case_id": case_id, "draft": services.get_draft(case_id), "synthetic": True}
