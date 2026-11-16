from .common import active, call

CLAUSES = {"UK": "UK FCA", "SG": "MAS Singapore", "US": "US FinCEN"}


async def tone(state):
    controls = active(state, "toner")["settings"]
    jurisdiction = CLAUSES[state["case"]["jurisdiction"]] if controls["jurisdiction_clause"] == "Auto" else controls["jurisdiction_clause"]
    fixture = dict(state["draft"])
    lead = "A friendly follow-up on the outstanding onboarding items." if controls["urgency"] == "3-Day Nudge" else "We would appreciate your help progressing these outstanding items." if controls["urgency"] == "Escalation" else ""
    fixture["body"] = fixture["body"].replace("Dear ", "Hello " if controls["formality"] < 40 else "Dear ", 1)
    fixture["body"] += f"\n\n{lead}\nOnboarding requirements: synthetic Northgate policy ({jurisdiction})."
    result, provider = await call(state, "toner", {"draft": state["draft"], "settings": controls, "jurisdiction": jurisdiction, "checklist": state["checklist"], "critique_feedback": state.get("feedback", [])}, fixture)
    return {"draft": result, "provider": provider}
