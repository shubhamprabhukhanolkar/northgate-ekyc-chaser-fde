import asyncio
import json
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import live
from app.agents.deterministic import gap_check
from app.config import settings
from app.db import connect, rows, now
from app.llm.preview import partial_string
from app.llm.router import router, ProviderUnavailable
from app.main import app

CID = "NG-2026-0841"
ACTOR = "rm@northgate.demo"


def test_partial_json_preview_decodes_only_email_fields():
    assert partial_string('{"subject":"Hello", "body":"Dear team,\\nPlease send', "body") == "Dear team,\nPlease send"
    assert partial_string('{"body":"Please use \\"one\\" reply"}', "body") == 'Please use "one" reply'
    assert partial_string('{"body":"A\\u20', "body") == "A"
    assert partial_string('{"body":"A\\u2022 B"}', "body") == "A• B"
    assert partial_string('{"plan":"Not an email"}', "body") == ""


async def test_live_run_is_deduplicated_persists_events_and_stays_human_gated():
    gap_check(CID, ACTOR)
    run = live.start(CID, ACTOR)
    assert live.start(CID, ACTOR)["id"] == run["id"]
    task = live.tasks[run["id"]]
    await task
    assert live.get_run(run["id"])["status"] == "COMPLETED"
    events = live.events(run["id"])
    assert [e["data"]["node"] for e in events if e["kind"] == "node_started"] == ["deterministic", "orchestrator", "drafter", "toner", "critique"]
    assert [e["data"]["agent"] for e in events if e["kind"] == "draft_preview"] == ["drafter", "toner"]
    assert events[-1]["kind"] == "run_completed"
    assert events[-1]["data"]["draft"]["status"] == "REVIEW"
    assert not rows("SELECT * FROM outbox")
    cursor = events[3]["id"]
    assert all(e["id"] > cursor for e in live.events(run["id"], cursor))
    assert not live.tasks


async def test_live_http_stream_replays_resumes_and_requires_auth():
    gap_check(CID, ACTOR)
    run = live.start(CID, ACTOR)
    await live.tasks[run["id"]]
    events = live.events(run["id"])
    client = TestClient(app)
    path = f"/api/runs/{run['id']}/events"
    assert client.get(path).status_code == 401
    client.post("/api/auth/login", json={"email": ACTOR, "password": "NorthgateDemo!2026"}).raise_for_status()
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert len(frames) == len(events)
    resumed = client.get(path, headers={"Last-Event-ID": str(events[-2]["id"])})
    frames = [json.loads(line[6:]) for line in resumed.text.splitlines() if line.startswith("data: ")]
    assert [e["kind"] for e in frames] == ["run_completed"]
    client.close()


async def test_streaming_provider_failure_resets_preview_and_records_failover(monkeypatch):
    settings().offline_demo = False
    with connect() as db:
        db.execute("INSERT INTO workflow_runs VALUES(?,?,?,?,?,?)", ("stream-test", CID, ACTOR, "RUNNING", now(), None))

    async def broken(system, payload, preview):
        preview.add('{"body":"Discard this partial primary text', force=True)
        raise TimeoutError()

    async def backup(system, payload, preview):
        text = json.dumps({"subject": "Backup draft", "body": "Replacement text from the backup provider", "requested_document_ids": []})
        for chunk in (text[:30], text[30:60], text[60:]):
            preview.add(chunk)
            await asyncio.sleep(0)
        preview.add("", force=True)
        return text, 100, 50

    monkeypatch.setattr(router, "gemini_stream", broken)
    monkeypatch.setattr(router, "groq_stream", backup)
    token = live.active_run.set("stream-test")
    try:
        result, provider = await router.call("drafter", "system", {}, CID)
    finally:
        live.active_run.reset(token)
    events = live.events("stream-test")
    assert provider == "groq"
    assert any(e["kind"] == "provider_failover" for e in events)
    assert [e["data"]["provider"] for e in events if e["kind"] == "preview_reset"] == ["gemini", "groq"]
    assert [e for e in events if e["kind"] == "draft_preview"][-1]["data"]["body"] == result["body"]
    ledger = rows("SELECT * FROM cost_ledger ORDER BY id")
    assert ledger[-1]["prompt_tokens"] == 100 and ledger[-1]["failover"] == 1


async def test_live_failure_is_terminal_and_keeps_existing_draft(monkeypatch):
    from app import services
    gap_check(CID, ACTOR)
    monkeypatch.setattr(services, "generate", AsyncMock(side_effect=ProviderUnavailable("Both providers unavailable")))
    run = live.start(CID, ACTOR)
    await live.tasks[run["id"]]
    assert live.get_run(run["id"])["status"] == "FAILED"
    assert live.events(run["id"])[-1]["kind"] == "run_failed"
    assert not rows("SELECT * FROM outbox")


async def test_groq_stream_uses_official_sdk_and_reads_final_usage(monkeypatch):
    import httpx
    from groq import AsyncGroq
    import app.llm.router as router_module
    from app.llm.preview import DraftPreview
    settings().groq_api_key = "test-only-key"

    def handler(request):
        assert json.loads(request.content)["stream"] is True
        common = {"id": "test-stream", "object": "chat.completion.chunk", "created": 1, "model": "test-model"}
        chunks = [
            {**common, "choices": [{"index": 0, "delta": {"content": '{"subject":"Hi","body":"Hello '}}]},
            {**common, "choices": [{"index": 0, "delta": {"content": 'team","requested_document_ids":[]}'}}], "x_groq": {"usage": {"prompt_tokens": 70, "completion_tokens": 20, "total_tokens": 90}}},
        ]
        content = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=content)

    monkeypatch.setattr(router_module, "AsyncGroq", lambda **kwargs: AsyncGroq(**kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))))
    preview = DraftPreview("drafter", "groq")
    text, incoming, outgoing = await router.groq_stream("system", {}, preview)
    assert json.loads(text)["body"] == "Hello team"
    assert (incoming, outgoing) == (70, 20)


def test_recovery_marks_interrupted_runs_and_read_before_write_still_applies():
    with pytest.raises(HTTPException):
        live.start(CID, ACTOR)
    with connect() as db:
        db.execute("INSERT INTO workflow_runs VALUES(?,?,?,?,?,?)", ("interrupted", CID, ACTOR, "RUNNING", now(), None))
    live.recover_interrupted()
    assert live.get_run("interrupted")["status"] == "INTERRUPTED"
    assert live.events("interrupted")[-1]["kind"] == "run_failed"


async def test_guided_instructions_reach_agents_and_are_audited(monkeypatch):
    from app.agents import common
    original = common.router.call
    captured = []
    instructions = "Use a warm concise greeting and a helpful closing."

    async def capture(agent, system, payload, case_id=None, fixture=None):
        captured.append((agent, payload.get("operator_drafting_instructions"), system))
        return await original(agent, system, payload, case_id, fixture)

    monkeypatch.setattr(common.router, "call", capture)
    gap_check(CID, ACTOR)
    with pytest.raises(HTTPException) as missing:
        live.start(CID, ACTOR, "guided", "")
    assert missing.value.status_code == 422
    assert not rows("SELECT * FROM workflow_runs")
    run = live.start(CID, ACTOR, "guided", instructions)
    await live.tasks[run["id"]]
    assert {item[0] for item in captured} == {"orchestrator", "drafter", "toner", "critique"}
    assert all(item[1] == instructions for item in captured)
    assert all("cannot authorize sending" in item[2] for item in captured)
    saved = rows("SELECT * FROM workflow_requests WHERE run_id=?", (run["id"],))[0]
    assert saved["mode"] == "guided" and saved["instructions"] == instructions
    audit = rows("SELECT * FROM audit WHERE action='draft_generated'")[0]
    assert json.loads(audit["payload"])["drafting_instructions"] == instructions
    assert live.events(run["id"])[-1]["data"]["draft"]["status"] == "REVIEW"
    assert not rows("SELECT * FROM outbox")


def test_expanded_seed_is_synthetic_balanced_and_idempotent():
    from app.db import initialize
    cases = rows("SELECT * FROM cases")
    assert len(cases) == 42
    assert len({case["id"] for case in cases}) == 42
    assert all(case["contact"].endswith("@example.com") for case in cases)
    assert {city: sum(case["city"] == city for case in cases) for city in ("London", "Singapore", "New York")} == {"London": 14, "Singapore": 14, "New York": 14}
    initialize()
    assert len(rows("SELECT * FROM cases")) == 42
