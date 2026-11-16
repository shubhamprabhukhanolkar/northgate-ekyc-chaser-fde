from .common import call


async def orchestrate(state):
    result, provider = await call(state, "orchestrator", {"gaps": state["checklist"]["missing"], "feedback": state.get("feedback", []), "attempt": state.get("attempts", 0)},
                                  {"plan": "Consolidate all outstanding documents; preserve the received-document lock; submit to RM."})
    return {"plan": result, "provider": provider, "attempts": state.get("attempts", 0)+1}
