import json
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from ..auth import current_user, require
from ..config import settings
from ..db import rows, connect, audit, now
from ..agents.deterministic import gap_check
from .. import services

router = APIRouter(prefix="/api", tags=["cases"])


class Decision(BaseModel):
    action: Literal["approve_send", "discard"]
    reason: str | None = Field(default=None, max_length=1000)
    draft_id: str


class Edit(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=30, max_length=20000)


@router.get("/cases")
def cases(jurisdiction: str | None = None, status: str | None = None, user=Depends(current_user)):
    return services.list_cases(jurisdiction, status)


@router.get("/cases/{case_id}")
def detail(case_id: str, user=Depends(current_user)):
    return {"checklist": gap_check(case_id, user["email"]), "draft": services.get_draft(case_id)}


@router.post("/cases/{case_id}/generate")
async def generate(case_id: str, user=Depends(require("rm", "analyst", "admin"))):
    return await services.generate(case_id, user["email"])


@router.put("/cases/{case_id}/draft")
async def edit(case_id: str, body: Edit, user=Depends(require("rm", "admin"))):
    return await services.edit_draft(case_id, user["email"], body.subject, body.body)


@router.post("/cases/{case_id}/decision")
def decision(case_id: str, body: Decision, user=Depends(require("rm", "admin"))):
    return services.decision(case_id, user["email"], body.action, body.reason, body.draft_id)


@router.post("/cases/{case_id}/mcp-approval-token")
def mcp_approval(case_id: str, user=Depends(require("rm", "admin"))):
    services.require_read(case_id, user["email"])
    draft = services.get_draft(case_id)
    if not draft or draft["status"] != "REVIEW":
        raise HTTPException(409, "A passing review draft is required")
    token = jwt.encode({"sub": user["email"], "purpose": "mcp_approve", "case_id": case_id, "draft_id": draft["id"],
                        "digest": services.prompt_digest({"subject": draft["subject"], "body": draft["body"]}),
                        "exp": datetime.now(timezone.utc)+timedelta(minutes=2)}, settings().auth_secret, algorithm="HS256")
    with connect() as db:
        audit(db, user["email"], "mcp_approval_authorized", case_id, {"draft_id": draft["id"]})
    return {"approval_token": token, "expires_in": 120}


@router.post("/cases/{case_id}/documents/{document_id}/receive")
def receive(case_id: str, document_id: str, user=Depends(require("analyst", "admin"))):
    with connect() as db:
        changed = db.execute("UPDATE documents SET status='RECEIVED',received_at=? WHERE case_id=? AND id=? AND status='MISSING'", (now(), case_id, document_id)).rowcount
        if changed:
            db.execute("UPDATE cases SET revision=revision+1 WHERE id=?", (case_id,))
            audit(db, user["email"], "synthetic_document_received", case_id, {"document_id": document_id})
        elif not db.execute("SELECT 1 FROM documents WHERE case_id=? AND id=?", (case_id, document_id)).fetchone():
            raise HTTPException(404, "Document not found")
    return gap_check(case_id, user["email"])


@router.post("/cases/{case_id}/reply")
def reply(case_id: str, user=Depends(require("rm", "analyst", "admin"))):
    gap_check(case_id)
    with connect() as db:
        db.execute("UPDATE cases SET replied_at=?,nudge_due=0,status='CLIENT_REPLIED' WHERE id=?", (now(), case_id))
        audit(db, user["email"], "client_reply_recorded", case_id)
    return {"ok": True}


@router.get("/traces")
def traces(case_id: str | None = None, user=Depends(current_user)):
    query = "SELECT * FROM traces" + (" WHERE case_id=?" if case_id else "") + " ORDER BY id DESC LIMIT 200"
    return [{**r, "payload": json.loads(r["payload"])} for r in rows(query, (case_id,) if case_id else ())]


@router.get("/audit")
def audit_log(user=Depends(require("admin", "coo"))):
    return rows("SELECT * FROM audit ORDER BY id DESC LIMIT 200")
