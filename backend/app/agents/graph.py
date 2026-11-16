import json
import uuid
import inspect
import time
from langgraph.graph import StateGraph, START, END
from .state import ChaseState
from .deterministic import gap_check
from .orchestrator import orchestrate
from .drafter import draft
from .toner import tone
from .critique import critique
from ..db import connect, now
from ..live import emit, active_run

DESCRIPTIONS = {
    "deterministic": "Checking the document store and locking received items.",
    "orchestrator": "Planning one consolidated request for the outstanding documents.",
    "drafter": "Writing a consolidated email from the missing-document checklist.",
    "toner": "Refining formality, urgency and jurisdiction wording.",
    "critique": "Checking document exclusions, completeness, claims and tone.",
}


def observable(name, function):
    async def invoke(state):
        iteration = state.get("attempts", 0) + (1 if name == "orchestrator" else 0)
        emit("node_started", node=name, iteration=max(1, iteration), summary=DESCRIPTIONS[name])
        started = time.perf_counter()
        try:
            result = function(state)
            if inspect.isawaitable(result):
                result = await result
        except Exception:
            emit("node_failed", node=name, summary=f"{name.title()} could not complete. The review gate stays locked.")
            raise
        details = {"node": name, "iteration": max(1, result.get("attempts", iteration)), "latency_ms": round((time.perf_counter()-started)*1000)}
        if name == "deterministic":
            checklist = result["checklist"]
            details["summary"] = f"{len(checklist['received'])} received documents locked; {len(checklist['missing'])} outstanding items identified."
        elif name == "critique":
            details["scorecard"] = result["scorecard"]
            details["summary"] = f"QA passed. Tone score {result['scorecard']['tone_score']}%." if result["scorecard"]["passed"] else "QA requested a revision: " + "; ".join(result["feedback"][:3])
        else:
            details["summary"] = {"orchestrator": "Consolidated chase plan prepared.", "drafter": "First wording prepared; Toner will refine it next.", "toner": "Tone-calibrated draft prepared for QA."}[name]
        if result.get("provider"):
            details["provider"] = result["provider"]
        emit("node_completed", **details)
        if name == "critique" and not result["scorecard"]["passed"] and state.get("attempts", 0) < 4:
            emit("revision", iteration=state.get("attempts", 1)+1, summary="Routing critique feedback back to the Orchestrator for a rewrite.", feedback=result["feedback"])
        return result
    return invoke


def deterministic(state):
    checklist = gap_check(state["case_id"])
    with connect() as db:
        db.execute("INSERT INTO traces(run_id,case_id,node,payload,created_at) VALUES(?,?,?,?,?)", (state["run_id"], state["case_id"], "deterministic", json.dumps(checklist), now()))
    return {"checklist": checklist, "case": checklist["case"]}


def compile_graph():
    graph = StateGraph(ChaseState)
    for name, fn in [("deterministic", deterministic), ("orchestrator", orchestrate), ("drafter", draft), ("toner", tone), ("critique", critique)]:
        graph.add_node(name, observable(name, fn))
    graph.add_edge(START, "deterministic")
    for a, b in [("deterministic", "orchestrator"), ("orchestrator", "drafter"), ("drafter", "toner"), ("toner", "critique")]:
        graph.add_edge(a, b)
    # Initial attempt plus at most three rewrites. A failed terminal draft stays locked.
    graph.add_conditional_edges("critique", lambda s: END if s["scorecard"]["passed"] or s["attempts"] >= 4 else "orchestrator", {END: END, "orchestrator": "orchestrator"})
    return graph.compile()


chase_graph = compile_graph()


async def run(case_id, overrides=None, instructions=""):
    return await chase_graph.ainvoke({"case_id": case_id, "run_id": active_run.get() or str(uuid.uuid4()), "attempts": 0, "overrides": overrides or {}, "drafting_instructions": instructions}, {"recursion_limit": 30})
