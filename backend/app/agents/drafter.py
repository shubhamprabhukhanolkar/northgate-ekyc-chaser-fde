from .common import call, fixture_draft


async def draft(state):
    result, provider = await call(state, "drafter", {"case": state["case"], "checklist": state["checklist"], "plan": state["plan"], "feedback": state.get("feedback", [])}, fixture_draft(state))
    return {"draft": result, "provider": provider}
