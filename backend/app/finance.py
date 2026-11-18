"""Deterministic financial rollups. Reads existing records; never calls an agent."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import ceil

from .config import settings
from .db import connect


def financial_summary(days=30):
    end = datetime.now(timezone.utc)
    start = (end - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0) if days else datetime(1970, 1, 1, tzinfo=timezone.utc)
    args = (start.isoformat(), end.isoformat())
    period = "julianday(created_at) BETWEEN julianday(?) AND julianday(?)"
    with connect() as db:
        db.execute("BEGIN")
        ledger = [dict(r) for r in db.execute(f"SELECT agent_name,provider,model,prompt_tokens,completion_tokens,latency_ms,cost_usd,cost_gbp,case_id,created_at,status,failover FROM cost_ledger WHERE {period} ORDER BY created_at", args)]
        actions = dict(db.execute(f"SELECT action,COUNT(*) FROM audit WHERE {period} GROUP BY action", args).fetchall())
        draft_status = dict(db.execute(f"SELECT status,COUNT(*) FROM drafts WHERE {period} GROUP BY status", args).fetchall())
        runs = dict(db.execute("SELECT status,COUNT(*) FROM workflow_runs WHERE julianday(started_at) BETWEEN julianday(?) AND julianday(?) GROUP BY status", args).fetchall())
        cases = [dict(r) for r in db.execute("SELECT id,jurisdiction,city,status,nudge_due FROM cases")]
        documents = dict(db.execute("SELECT status,COUNT(*) FROM documents GROUP BY status").fetchall())
        revisions = db.execute(f"SELECT COUNT(*) FROM workflow_events WHERE {period} AND kind='revision'", args).fetchone()[0]
        outbox = db.execute(f"SELECT COUNT(*) FROM outbox WHERE {period}", args).fetchone()[0]

    def bucket():
        return {"calls": 0, "cost_gbp": 0.0, "cost_usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "errors": 0, "failovers": 0, "latencies": []}

    def add(target, row):
        target["calls"] += 1
        for key in ("cost_gbp", "cost_usd", "prompt_tokens", "completion_tokens"):
            target[key] += row[key] or 0
        target["errors"] += row["status"] == "error"
        target["failovers"] += bool(row["failover"]) and row["status"] == "success"
        target["latencies"].append(max(0, row["latency_ms"] or 0))

    def clean(target):
        latencies = sorted(target["latencies"])
        return {k: v for k, v in target.items() if k != "latencies"} | {
            "average_latency_ms": sum(latencies) / len(latencies) if latencies else None,
            "p95_latency_ms": latencies[max(0, ceil(len(latencies) * .95) - 1)] if latencies else None,
        }

    real = [row for row in ledger if row["provider"] in ("gemini", "groq")]
    totals = bucket()
    agents, providers, case_costs = defaultdict(bucket), defaultdict(bucket), defaultdict(bucket)
    day_costs = defaultdict(lambda: {"cost_gbp": 0.0, "calls": 0})
    for row in real:
        add(totals, row)
        add(agents[row["agent_name"]], row)
        add(providers[(row["provider"], row["model"] or "unknown")], row)
        if row["case_id"]:
            add(case_costs[row["case_id"]], row)
        date = datetime.fromisoformat(row["created_at"]).astimezone(timezone.utc).date().isoformat()
        day_costs[date]["cost_gbp"] += row["cost_gbp"] or 0
        day_costs[date]["calls"] += 1
    result = clean(totals)
    case_spend = sum(v["cost_gbp"] for v in case_costs.values())
    result.update({"case_cost_gbp": case_spend, "non_case_cost_gbp": result["cost_gbp"] - case_spend,
                   "costed_cases": len(case_costs), "average_case_cost_gbp": case_spend / len(case_costs) if case_costs else None,
                   "average_call_cost_gbp": result["cost_gbp"] / result["calls"] if result["calls"] else None,
                   "error_rate": result["errors"] / result["calls"] if result["calls"] else None,
                   "offline_fixture_calls": sum(row["provider"] == "offline_demo" for row in ledger)})
    by_id = {case["id"]: case for case in cases}
    jurisdictions = {}
    for region in ("UK", "SG", "US"):
        sample = [case for case in cases if case["jurisdiction"] == region]
        associated = [case_costs[case["id"]] for case in sample if case["id"] in case_costs]
        cost = sum(row["cost_gbp"] for row in associated)
        jurisdictions[region] = {"cases": len(sample), "costed_cases": len(associated), "cost_gbp": cost,
                                 "average_case_cost_gbp": cost / len(associated) if associated else None,
                                 "nudge_due": sum(bool(case["nudge_due"]) for case in sample)}
    today = end.replace(hour=0, minute=0, second=0, microsecond=0)
    if days:
        trend_start = max(start, today - timedelta(days=89))
    elif real:
        first = datetime.fromisoformat(real[0]["created_at"]).astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        trend_start = max(first, today - timedelta(days=89))
    else:
        trend_start = today - timedelta(days=29)
    trend = []
    cursor = trend_start.date()
    while cursor <= end.date():
        value = day_costs[cursor.isoformat()]
        trend.append({"date": cursor.isoformat(), **value})
        cursor += timedelta(days=1)
    reviewed = actions.get("approve_send", 0) + actions.get("discard", 0)
    return {
        "period": {"days": days, "start": start.isoformat(), "end": end.isoformat(), "timezone": "UTC"},
        "totals": result,
        "agents": [{"agent": agent, **clean(value)} for agent, value in sorted(agents.items())],
        "providers": [{"provider": key[0], "model": key[1], **clean(value)} for key, value in sorted(providers.items())],
        "daily": trend,
        "case_costs": [{"case_id": key, "jurisdiction": by_id.get(key, {}).get("jurisdiction", "Unknown"), **clean(value)} for key, value in sorted(case_costs.items(), key=lambda item: item[1]["cost_gbp"], reverse=True)[:25]],
        "jurisdictions": jurisdictions,
        "activity": {"case_inventory": len(cases), "case_statuses": {status: sum(case["status"] == status for case in cases) for status in sorted({case["status"] for case in cases})},
                     "documents": documents, "drafts_created": sum(draft_status.values()), "draft_statuses": draft_status,
                     "generated": actions.get("draft_generated", 0), "approved": actions.get("approve_send", 0), "discarded": actions.get("discard", 0),
                     "edited": actions.get("draft_edited_and_rechecked", 0), "synthetic_outbox": outbox,
                     "discard_rate": actions.get("discard", 0) / reviewed if reviewed else None,
                     "workflow_runs": runs, "rewrite_events": revisions},
        "pricing": {"usd_to_gbp": settings().usd_to_gbp,
                    "gemini_input": settings().gemini_input_per_million, "gemini_output": settings().gemini_output_per_million,
                    "groq_input": settings().groq_input_per_million, "groq_output": settings().groq_output_per_million},
        "limitations": ["Recorded costs are token-based estimates, not vendor invoices. Failures before usage is returned are logged with zero tokens and can understate billed spend.",
                        "Offline fixture calls are excluded from cost denominators. Case unit cost includes all provider attempts attributed to each touched case, including rewrites and regression tests; costs cannot be allocated exactly to individual runs because the ledger has no run ID.",
                        "Inventory and document counts are current snapshots. Draft status is current for drafts created in the selected window. Review counts use audit action dates; runs use start dates. Trend shows at most 90 UTC days.",
                        "Cloud billing, staff time, revenue uplift and realized cash savings are not collected. Resource costs and savings in the planner are assumptions, never booked financial results.",
                        "This lab uses instance-local SQLite; history and CFO assumptions are not a durable financial record. Planner inputs remain in the browser page until reload."],
    }
