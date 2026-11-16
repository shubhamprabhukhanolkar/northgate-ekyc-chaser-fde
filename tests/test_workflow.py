import json
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from app.agents.deterministic import gap_check
from app.agents.critique import deterministic_score
from app.agents.common import fixture_draft
from app.agents.graph import run
from app.db import connect, rows
from app import services

CID = "NG-2026-0841"
ACTOR = "rm@northgate.demo"


def test_received_lock_rejects_false_chase():
    checklist = gap_check(CID)
    draft = fixture_draft({"case": checklist["case"], "case_id": CID, "checklist": checklist})
    assert all(deterministic_score(draft, checklist).values())
    draft["body"] += "\nPlease also supply " + checklist["received"][0]["name"]
    assert not deterministic_score(draft, checklist)["zero_false_chases"]
    draft["requested_document_ids"].append(checklist["received"][0]["id"])
    assert not deterministic_score(draft, checklist)["all_missing_consolidated"]


async def test_critique_loops_a_deliberately_flawed_draft(monkeypatch):
    from app.agents import common
    original = common.router.call
    drafts = 0

    async def injected(agent, system, payload, case_id=None, fixture=None):
        nonlocal drafts
        if agent == "drafter":
            drafts += 1
            if drafts == 1:
                fixture = {**fixture, "body": fixture["body"] + "\nPlease provide ACRA business profile."}
        return await original(agent, system, payload, case_id, fixture)
    monkeypatch.setattr(common.router, "call", injected)
    result = await run(CID)
    assert result["attempts"] == 2
    assert result["scorecard"]["passed"]
    assert len(rows("SELECT * FROM traces WHERE node='critique'")) == 2


async def test_persistent_failure_never_unlocks_review(monkeypatch):
    from app.agents import common
    original = common.router.call

    async def broken(agent, system, payload, case_id=None, fixture=None):
        if agent == "toner":
            fixture = {**fixture, "body": fixture["body"] + " This is high risk."}
        return await original(agent, system, payload, case_id, fixture)
    monkeypatch.setattr(common.router, "call", broken)
    gap_check(CID, ACTOR)
    result = await services.generate(CID, ACTOR)
    assert result["status"] == "BLOCKED"
    assert result["scorecard"]["iterations"] == 4
    with pytest.raises(HTTPException):
        services.decision(CID, ACTOR, "approve_send")
    assert not rows("SELECT * FROM outbox")


async def test_cost_ledger_records_all_agents_and_human_gate():
    gap_check(CID, ACTOR)
    draft = await services.generate(CID, ACTOR)
    assert draft["status"] == "REVIEW"
    assert not rows("SELECT * FROM outbox")
    steps = rows("SELECT agent_name FROM cost_ledger")
    assert {r["agent_name"] for r in steps} == {"orchestrator", "drafter", "toner", "critique"}
    assert len(rows("SELECT * FROM traces")) == 5
    services.decision(CID, ACTOR, "approve_send", expected_draft_id=draft["id"])
    assert len(rows("SELECT * FROM outbox")) == 1
    with pytest.raises(HTTPException):
        services.decision(CID, ACTOR, "approve_send")


async def test_document_arriving_during_rm_review_blocks_send():
    gap_check(CID, ACTOR)
    await services.generate(CID, ACTOR)
    with connect() as db:
        db.execute("UPDATE documents SET status='RECEIVED' WHERE case_id=? AND id='ubo'", (CID,))
        db.execute("UPDATE cases SET revision=revision+1 WHERE id=?", (CID,))
    with pytest.raises(HTTPException):
        services.decision(CID, ACTOR, "approve_send")
    assert not rows("SELECT * FROM outbox")


async def test_edits_run_qa_again():
    gap_check(CID, ACTOR)
    draft = await services.generate(CID, ACTOR)
    changed = await services.edit_draft(CID, ACTOR, draft["subject"], draft["body"] + "\nYour documents are authentic.")
    assert changed["status"] == "BLOCKED"
    with pytest.raises(HTTPException):
        services.decision(CID, ACTOR, "approve_send")


def test_read_before_write():
    with pytest.raises(HTTPException):
        services.require_read(CID, "unknown_actor")


def test_audit_append_only():
    import sqlite3
    from app.db import audit
    with connect() as db:
        audit(db, ACTOR, "test", CID)
    with pytest.raises(sqlite3.IntegrityError):
        with connect() as db:
            db.execute("DELETE FROM audit")
