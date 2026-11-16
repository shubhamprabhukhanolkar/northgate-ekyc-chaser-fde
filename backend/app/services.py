import asyncio
import json
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from .db import rows, connect, audit, now, prompt
from .agents.deterministic import gap_check
from .agents.graph import run
from .agents.critique import critique, deterministic_score
from .llm.pricing import roi

case_locks: dict[str, asyncio.Lock] = {}


def list_cases(jurisdiction=None, status=None):
    result = rows('''SELECT c.*, (SELECT count(*) FROM documents d WHERE d.case_id=c.id AND d.status='MISSING') missing_count,
        (SELECT count(*) FROM documents d WHERE d.case_id=c.id AND d.status='RECEIVED') received_count,
        (SELECT id FROM drafts d WHERE d.case_id=c.id ORDER BY created_at DESC LIMIT 1) draft_id FROM cases c ORDER BY id''')
    return [r for r in result if (not jurisdiction or r["jurisdiction"] == jurisdiction or r["city"] == jurisdiction) and (not status or r["status"] == status)]


def get_draft(case_id):
    result = rows("SELECT * FROM drafts WHERE case_id=? ORDER BY created_at DESC LIMIT 1", (case_id,))
    if not result:
        return None
    d = result[0]
    return {**d, "requested_document_ids": json.loads(d["requested_ids"]), "scorecard": json.loads(d["scorecard"])}


def require_read(case_id, actor):
    found = rows("SELECT * FROM read_receipts WHERE actor=? AND case_id=?", (actor, case_id))
    current = gap_check(case_id)
    if not found or found[0]["revision"] != current["revision"]:
        raise HTTPException(409, "Read the current gap checklist before writing")
    return current


async def generate(case_id, actor):
    async with case_locks.setdefault(case_id, asyncio.Lock()):
        before = require_read(case_id, actor)
        if not before["missing"]:
            raise HTTPException(409, "No missing documents; no chase is needed")
        overrides = {}
        if before["case"]["nudge_due"]:
            controls = json.loads(prompt("toner")["settings"])
            controls["urgency"] = "3-Day Nudge"
            overrides = {"toner": {"settings": controls}}
        result = await run(case_id, overrides)
        draft = result["draft"]
        did = str(uuid.uuid4())
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT revision FROM cases WHERE id=?", (case_id,)).fetchone()
            if current["revision"] != before["revision"]:
                raise HTTPException(409, "Document store changed during generation; read the checklist and regenerate")
            passed = result["scorecard"]["passed"]
            db.execute("UPDATE drafts SET status='SUPERSEDED' WHERE case_id=? AND status='REVIEW'", (case_id,))
            db.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?,?,?,?,?)", (did, case_id, draft.get("subject", ""), draft.get("body", ""),
                json.dumps(draft.get("requested_document_ids", [])), json.dumps(result["scorecard"]), "REVIEW" if passed else "BLOCKED", before["revision"], now(), result["provider"]))
            db.execute("UPDATE cases SET status=? WHERE id=?", ("RM_REVIEW" if passed else "QA_BLOCKED", case_id))
            audit(db, actor, "draft_generated", case_id, {"draft_id": did, "scorecard": result["scorecard"], "run_id": result["run_id"]})
        return get_draft(case_id)


async def edit_draft(case_id, actor, subject, body):
    async with case_locks.setdefault(case_id, asyncio.Lock()):
        checklist = require_read(case_id, actor)
        existing = get_draft(case_id)
        if not existing or existing["status"] != "REVIEW":
            raise HTTPException(409, "No editable review draft")
        edited = {"subject": subject, "body": body, "requested_document_ids": existing["requested_document_ids"]}
        result = await critique({"case_id": case_id, "run_id": str(uuid.uuid4()), "draft": edited, "checklist": checklist, "attempts": 1})
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT revision FROM cases WHERE id=?", (case_id,)).fetchone()
            if current["revision"] != checklist["revision"] or existing["gap_revision"] != checklist["revision"]:
                raise HTTPException(409, "Document store changed; regenerate")
            changed = db.execute("UPDATE drafts SET subject=?,body=?,scorecard=?,status=? WHERE id=? AND status='REVIEW'", (subject, body, json.dumps(result["scorecard"]), "REVIEW" if result["scorecard"]["passed"] else "BLOCKED", existing["id"])).rowcount
            if changed != 1:
                raise HTTPException(409, "Draft changed; reload")
            audit(db, actor, "draft_edited_and_rechecked", case_id, {"draft_id": existing["id"], "scorecard": result["scorecard"]})
        return get_draft(case_id)


def decision(case_id, actor, action, reason=None, expected_draft_id=None):
    require_read(case_id, actor)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        draft = db.execute("SELECT * FROM drafts WHERE case_id=? ORDER BY created_at DESC LIMIT 1", (case_id,)).fetchone()
        case = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not draft or draft["status"] not in ("REVIEW", "BLOCKED"):
            raise HTTPException(409, "No pending draft; decision may already have been recorded")
        if expected_draft_id and draft["id"] != expected_draft_id:
            raise HTTPException(409, "Approval belongs to an older draft")
        if action == "approve_send":
            checklist = {"missing": [], "received": []}
            for doc in db.execute("SELECT * FROM documents WHERE case_id=?", (case_id,)):
                checklist["missing" if doc["status"] == "MISSING" else "received"].append(dict(doc))
            content = {"subject": draft["subject"], "body": draft["body"], "requested_document_ids": json.loads(draft["requested_ids"])}
            if draft["status"] != "REVIEW" or not json.loads(draft["scorecard"])["passed"] or draft["gap_revision"] != case["revision"] or not all(deterministic_score(content, checklist).values()):
                raise HTTPException(409, "Safety gate failed or document store changed; regenerate the draft")
            # Synthetic transport: durable demo outbox; never contact a real client.
            db.execute("INSERT INTO outbox VALUES(?,?,?,?,?)", (str(uuid.uuid4()), draft["id"], case_id, json.dumps({"to": case["contact"], **content, "transport": "synthetic_outbox"}), now()))
            db.execute("UPDATE drafts SET status='SENT' WHERE id=?", (draft["id"],))
            db.execute("UPDATE cases SET status='AWAITING_REPLY',last_sent_at=?,replied_at=NULL,nudge_due=0 WHERE id=?", (now(), case_id))
        elif action == "discard":
            if not reason or not reason.strip():
                raise HTTPException(422, "A discard reason is required")
            db.execute("UPDATE drafts SET status='DISCARDED' WHERE id=?", (draft["id"],))
            db.execute("UPDATE cases SET status='NEEDS_DRAFT' WHERE id=?", (case_id,))
        else:
            raise HTTPException(422, "Unknown action")
        audit(db, actor, action, case_id, {"draft_id": draft["id"], "reason": reason, "transport": "synthetic_outbox"})
    return {"action": action, "draft_id": draft["id"], "transport": "synthetic_outbox", "message": "Recorded in synthetic outbox; no external email sent" if action == "approve_send" else "Draft discarded"}


def finops():
    totals = rows("SELECT COALESCE(SUM(cost_usd),0) cost_usd, COALESCE(SUM(cost_gbp),0) cost_gbp, COALESCE(SUM(prompt_tokens),0) prompt_tokens, COALESCE(SUM(completion_tokens),0) completion_tokens, COALESCE(SUM(failover),0) failovers, COUNT(*) calls FROM cost_ledger")[0]
    counts = rows("SELECT COUNT(*) total, COALESCE(SUM(status='DISCARDED'),0) discarded FROM drafts WHERE status IN ('DISCARDED','SENT')")[0]
    return {**totals, "agents": rows("SELECT agent_name,provider,COUNT(*) calls,SUM(cost_usd) cost_usd,SUM(cost_gbp) cost_gbp,SUM(prompt_tokens) prompt_tokens,SUM(completion_tokens) completion_tokens,AVG(latency_ms) latency_ms FROM cost_ledger GROUP BY agent_name,provider"),
        "cases": rows("SELECT case_id,SUM(cost_usd) cost_usd FROM cost_ledger GROUP BY case_id"),
        "providers": rows("SELECT provider,status,COUNT(*) calls FROM cost_ledger GROUP BY provider,status"),
        "discard_rate": counts["discarded"] / counts["total"] if counts["total"] else 0,
        "roi": roi(), "ledger": rows("SELECT * FROM cost_ledger ORDER BY id DESC LIMIT 100")}


def prompt_digest(overrides):
    return hashlib.sha256(json.dumps(overrides, sort_keys=True).encode()).hexdigest()


async def regression(overrides):
    results = []
    for case in list_cases()[:5]:
        result = await run(case["id"], overrides)
        results.append({"case_id": case["id"], "scorecard": result["scorecard"]})
    rid = str(uuid.uuid4())
    output = {"id": rid, "passed": all(r["scorecard"]["passed"] for r in results), "results": results}
    with connect() as db:
        db.execute("INSERT INTO regression VALUES(?,?,?,?)", (rid, prompt_digest(overrides), json.dumps(output), now()))
    return output
