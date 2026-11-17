from app.agents.copilot import query, retrieve
from app.db import rows
import json
from pathlib import Path
import re
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.agents.portal_help import PORTAL_HELP, PORTAL_PAGES, STARTER_QUESTIONS
from app.main import app


def test_product_help_retrieval_matches_current_portal_controls():
    references = retrieve("Where do I change Auto-draft and Guided draft?")
    assert references[0]["id"] == "NG-PORTAL-02"
    assert "top bar" in references[0]["text"] and "before Audio" in references[0]["text"]
    references = retrieve("How can I browse six cases per page with Previous and Next?")
    assert references[0]["id"] == "NG-PORTAL-01"
    references = retrieve("Does Agent Trace have Draft or Redraft controls?")
    assert any(source["id"] == "NG-PORTAL-06" and "no Draft or Redraft" in source["text"] for source in references)


def test_guidance_references_cover_both_modes_and_follow_up_context():
    references = retrieve("Where do I put redrafting instructions and optional guidance?")
    source = next(source for source in references if source["id"] == "NG-PORTAL-03")
    assert "below the workflow animation" in source["text"]
    assert "Auto-draft guidance is optional" in source["text"]
    follow_up = retrieve("Where is it?", [{"role":"user","content":"I need help choosing Auto-draft or Guided draft"}])
    assert any(source["id"] == "NG-PORTAL-02" for source in follow_up)


async def test_portal_guide_is_grounded_and_logs_its_agent_trace(monkeypatch):
    from app.agents import copilot
    original = copilot.router.call
    captured = []
    async def capture(agent, system, payload, case_id=None, fixture=None):
        captured.append((system,payload))
        return await original(agent,system,payload,case_id,fixture)
    monkeypatch.setattr(copilot.router,"call",capture)
    history = [{"role":"user","content":"I want to create my first draft"}]
    result = await query("How do I use Guided draft?", history)
    assert result["citations"]
    assert any(source["id"].startswith("NG-PORTAL-") for source in result["citations"])
    assert "PRIMARY purpose" in captured[0][0]
    assert captured[0][1]["conversation"] == history
    trace = rows("SELECT * FROM traces WHERE node='policy_copilot'")
    assert len(trace) == 1 and trace[0]["case_id"] is None
    assert rows("SELECT * FROM cost_ledger")[0]["agent_name"] == "policy_copilot"


@pytest.mark.parametrize("question, reference", [
    ("How do I upload a file and mark a missing document received?", "NG-PORTAL-16"),
    ("Why is Approve & Send greyed out after I edit?", "NG-PORTAL-20"),
    ("Where do I download a report of token costs?", "NG-PORTAL-19"),
    ("My Gemini connection expired. How do I reconnect or disconnect?", "NG-PORTAL-21"),
    ("Can Gemini generate or send emails through my read-only connection?", "NG-PORTAL-21"),
    ("How do I use the two-minute MCP approval token?", "NG-PORTAL-21"),
    ("Where do I record a client reply to stop follow-ups?", "NG-PORTAL-07"),
    ("How do I save a prompt version after running the regression test?", "NG-PORTAL-08"),
    ("What does QA blocked mean and why is the tone score 95?", "NG-PORTAL-17"),
    ("What can I do as a COO?", "NG-PORTAL-15"),
    ("Does sound start on and how do I mute it?", "NG-PORTAL-11"),
    ("Why can't I mark a document received as an RM?", "NG-PORTAL-15"),
    ("What does Superseded mean?", "NG-PORTAL-18"),
    ("Where are Portal Guide conversations in Agent Trace?", "NG-PORTAL-06"),
])
def test_operational_questions_have_relevant_sources(question, reference):
    assert reference in {source["id"] for source in retrieve(question)}


def test_every_navigation_page_and_starter_has_maintained_guidance():
    layout = (Path(__file__).resolve().parents[1] / "frontend/src/components/Layout.tsx").read_text(encoding="utf-8")
    actual_pages = dict(re.findall(r'\["(/[^\"]*)", "([^\"]+)",', layout))
    assert {path: page["label"] for path, page in PORTAL_PAGES.items()} == actual_pages
    reference_ids = [source["id"] for source in PORTAL_HELP]
    assert len(reference_ids) == len(set(reference_ids))
    assert all(page["reference"] in reference_ids for page in PORTAL_PAGES.values())
    assert len({s["id"] for s in STARTER_QUESTIONS}) == len(STARTER_QUESTIONS)
    for starter in STARTER_QUESTIONS:
        assert starter["question"].endswith("?")
        assert starter["reference"] in {source["id"] for source in retrieve(starter["question"])}
    assert retrieve("Walk me through the whole portal and all screens")[0]["id"] == "NG-PORTAL-14"


def test_follow_up_retrieval_keeps_the_operational_topic():
    sources = retrieve("And how do I disconnect it?", [{"role": "user", "content": "I want to connect my Gemini account for read-only access"}])
    assert any(source["id"] == "NG-PORTAL-21" for source in sources)


def test_help_endpoint_and_trusted_role_context(monkeypatch):
    from app.routes import copilot_routes
    captured = AsyncMock(return_value={"answer": "Read-only role", "citations": [], "provider": "test"})
    monkeypatch.setattr(copilot_routes, "query", captured)
    client = TestClient(app)
    assert client.get("/api/policy/help").status_code == 401
    client.post("/api/auth/login", json={"email": "coo@northgate.demo", "password": "NorthgateDemo!2026"}).raise_for_status()
    response = client.get("/api/policy/help")
    assert response.status_code == 200
    assert [s["question"] for s in response.json()["suggestions"]] == [s["question"] for s in STARTER_QUESTIONS]
    assert all("reference" not in s for s in response.json()["suggestions"])
    client.post("/api/policy/query", json={"question": "Why can't I draft?", "draft_mode": "guided", "operator_role": "admin"}).raise_for_status()
    assert captured.call_args.kwargs == {"operator_role": "coo", "draft_mode": "guided"}
    client.close()


async def test_query_receives_role_and_screen_index_without_private_configuration(monkeypatch):
    from app.agents import copilot
    captured = AsyncMock(return_value=({"answer": "Use the Audio toggle in the top bar.", "citations": ["NG-PORTAL-11"]}, "test"))
    monkeypatch.setattr(copilot.router, "call", captured)
    result = await query("How do I turn audio off?", operator_role="coo", draft_mode="guided")
    payload = captured.call_args.args[2]
    assert payload["portal_context"]["operator_role"] == "coo"
    assert payload["portal_context"]["draft_mode"] == "guided"
    assert len(payload["portal_context"]["available_screens"]) == 8
    assert "auth_secret" not in json.dumps(payload).lower()
    assert result["citations"][0]["id"] == "NG-PORTAL-11"


async def test_unsupported_question_does_not_invent_an_answer(monkeypatch):
    from app.agents import copilot
    captured = AsyncMock()
    monkeypatch.setattr(copilot.router, "call", captured)
    result = await query("Calculate quantum entanglement wavelengths")
    assert not captured.called
    assert result["citations"] == []
    assert "don't have a verified answer" in result["answer"]


async def test_unverified_citations_do_not_pass_through_model_answer(monkeypatch):
    from app.agents import copilot
    monkeypatch.setattr(copilot.router, "call", AsyncMock(return_value=({"answer": "I uploaded the file and approved it.", "citations": ["MADE-UP"]}, "test")))
    result = await query("How do I upload a file?")
    assert "I uploaded" not in result["answer"]
    assert result["citations"] == []
