"""Persisted, reconnectable workflow events. Only public action summaries are emitted."""
import asyncio
import contextvars
import json
import uuid
from fastapi import HTTPException
from .db import connect, rows, now

active_run = contextvars.ContextVar("northgate_live_run", default=None)
tasks: dict[str, asyncio.Task] = {}


def emit(kind, **data):
    run_id = active_run.get()
    if run_id:
        with connect() as db:
            db.execute("INSERT INTO workflow_events(run_id,kind,data,created_at) VALUES(?,?,?,?)", (run_id, kind, json.dumps(data), now()))


def get_run(run_id):
    found = rows("SELECT * FROM workflow_runs WHERE id=?", (run_id,))
    if not found:
        raise HTTPException(404, "Workflow run not found")
    return found[0]


def events(run_id, after=0):
    return [{**r, "data": json.loads(r["data"])} for r in rows("SELECT * FROM workflow_events WHERE run_id=? AND id>? ORDER BY id LIMIT 500", (run_id, after))]


async def execute(run_id, case_id, actor, mode="auto", instructions=""):
    from .services import generate
    token = active_run.set(run_id)
    try:
        emit("run_started", case_id=case_id, mode=mode, instructions=instructions, summary="Preparing a draft using your instructions." if mode == "guided" else "Automatically preparing your consolidated draft.")
        draft = await generate(case_id, actor, instructions=instructions)
        emit("run_completed", draft=draft, passed=draft["scorecard"]["passed"], summary="Draft passed QA and is ready for RM review." if draft["scorecard"]["passed"] else "Revision budget exhausted. Draft remains blocked for review.")
        with connect() as db:
            db.execute("UPDATE workflow_runs SET status=?,finished_at=? WHERE id=?", ("COMPLETED" if draft["scorecard"]["passed"] else "BLOCKED", now(), run_id))
    except asyncio.CancelledError:
        emit("run_failed", summary="The server restarted before this run finished. You can start a fresh generation.")
        with connect() as db:
            db.execute("UPDATE workflow_runs SET status='INTERRUPTED',finished_at=? WHERE id=?", (now(), run_id))
        raise
    except Exception as exc:
        from .llm.router import ProviderUnavailable
        message = str(exc) if isinstance(exc, ProviderUnavailable) else str(exc.detail) if isinstance(exc, HTTPException) else "The workflow stopped unexpectedly. Please retry generation."
        emit("run_failed", summary=message)
        with connect() as db:
            db.execute("UPDATE workflow_runs SET status='FAILED',finished_at=? WHERE id=?", (now(), run_id))
    finally:
        active_run.reset(token)
        tasks.pop(run_id, None)


def start(case_id, actor, mode="auto", instructions=""):
    from .services import require_read
    instructions = instructions.strip()
    if mode not in ("auto", "guided") or len(instructions) > 3000 or (mode == "guided" and len(instructions) < 5):
        raise HTTPException(422, "Guided drafts need 5–3000 characters of drafting instructions")
    checklist = require_read(case_id, actor)
    if not checklist["missing"]:
        raise HTTPException(409, "No missing documents; no chase is needed")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT * FROM workflow_runs WHERE case_id=? AND status='RUNNING'", (case_id,)).fetchone()
        if existing:
            return dict(existing)
        run_id = str(uuid.uuid4())
        db.execute("INSERT INTO workflow_runs VALUES(?,?,?,?,?,?)", (run_id, case_id, actor, "RUNNING", now(), None))
        db.execute("INSERT INTO workflow_requests VALUES(?,?,?)", (run_id, mode, instructions))
    tasks[run_id] = asyncio.create_task(execute(run_id, case_id, actor, mode, instructions))
    return get_run(run_id)


def recover_interrupted():
    with connect() as db:
        found = db.execute("SELECT id FROM workflow_runs WHERE status='RUNNING'").fetchall()
        for row in found:
            db.execute("INSERT INTO workflow_events(run_id,kind,data,created_at) VALUES(?,?,?,?)", (row["id"], "run_failed", json.dumps({"summary": "Server restarted. This run was interrupted; generate a fresh draft."}), now()))
        db.execute("UPDATE workflow_runs SET status='INTERRUPTED',finished_at=? WHERE status='RUNNING'", (now(),))


async def shutdown():
    running = list(tasks.values())
    for task in running:
        task.cancel()
    if running:
        await asyncio.gather(*running, return_exceptions=True)
