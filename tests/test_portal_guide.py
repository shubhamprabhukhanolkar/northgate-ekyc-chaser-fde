from app.agents.copilot import query, retrieve
from app.db import rows


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
