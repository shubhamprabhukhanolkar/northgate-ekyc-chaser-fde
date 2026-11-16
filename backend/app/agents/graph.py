import json
import uuid
from langgraph.graph import StateGraph, START, END
from .state import ChaseState
from .deterministic import gap_check
from .orchestrator import orchestrate
from .drafter import draft
from .toner import tone
from .critique import critique
from ..db import connect, now


def deterministic(state):
    checklist = gap_check(state["case_id"])
    with connect() as db:
        db.execute("INSERT INTO traces(run_id,case_id,node,payload,created_at) VALUES(?,?,?,?,?)", (state["run_id"], state["case_id"], "deterministic", json.dumps(checklist), now()))
    return {"checklist": checklist, "case": checklist["case"]}


def compile_graph():
    graph = StateGraph(ChaseState)
    for name, fn in [("deterministic", deterministic), ("orchestrator", orchestrate), ("drafter", draft), ("toner", tone), ("critique", critique)]:
        graph.add_node(name, fn)
    graph.add_edge(START, "deterministic")
    for a, b in [("deterministic", "orchestrator"), ("orchestrator", "drafter"), ("drafter", "toner"), ("toner", "critique")]:
        graph.add_edge(a, b)
    # Initial attempt plus at most three rewrites. A failed terminal draft stays locked.
    graph.add_conditional_edges("critique", lambda s: END if s["scorecard"]["passed"] or s["attempts"] >= 4 else "orchestrator", {END: END, "orchestrator": "orchestrator"})
    return graph.compile()


chase_graph = compile_graph()


async def run(case_id, overrides=None):
    return await chase_graph.ainvoke({"case_id": case_id, "run_id": str(uuid.uuid4()), "attempts": 0, "overrides": overrides or {}}, {"recursion_limit": 30})
