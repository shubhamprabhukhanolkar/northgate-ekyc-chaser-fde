"""Read-only governance evidence from existing records. No agent execution."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from .db import connect


def obj(value):
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def risk_summary(days=30):
    end = datetime.now(timezone.utc)
    start = (end - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0) if days else datetime(1970, 1, 1, tzinfo=timezone.utc)
    period = "julianday(created_at) BETWEEN julianday(?) AND julianday(?)"
    args = (start.isoformat(), end.isoformat())
    with connect() as db:
        db.execute("BEGIN")
        drafts = [dict(row) for row in db.execute("SELECT id,case_id,status,scorecard,gap_revision,created_at FROM drafts ORDER BY julianday(created_at) DESC,id DESC")]
        cases = [dict(row) for row in db.execute("SELECT id,jurisdiction,revision,status,nudge_due FROM cases ORDER BY id")]
        audit = [dict(row) for row in db.execute(f"SELECT id,actor,action,case_id,payload,created_at FROM audit WHERE {period} ORDER BY id DESC", args)]
        approvals = [dict(row) for row in db.execute("SELECT actor,case_id,payload,created_at FROM audit WHERE action='approve_send' AND julianday(created_at)<=julianday(?)", (end.isoformat(),))]
        outbox = [dict(row) for row in db.execute(f"SELECT id,draft_id,case_id,created_at FROM outbox WHERE {period}", args)]
        events = [dict(row) for row in db.execute(f"SELECT run_id,kind,data,created_at FROM workflow_events WHERE {period} AND kind IN ('node_completed','revision')", args)]
        providers = [dict(row) for row in db.execute(f"SELECT provider,status,COUNT(*) calls,SUM(failover) failovers FROM cost_ledger WHERE {period} AND provider IN ('gemini','groq') GROUP BY provider,status", args)]
        runs = dict(db.execute("SELECT status,COUNT(*) FROM workflow_runs WHERE julianday(started_at) BETWEEN julianday(?) AND julianday(?) GROUP BY status", args).fetchall())
        documents = dict(db.execute("SELECT status,COUNT(*) FROM documents GROUP BY status").fetchall())
        roles = dict(db.execute("SELECT email,role FROM users").fetchall())
        audit_coverage = dict(db.execute("SELECT COUNT(*) total,SUM(CASE WHEN julianday(retain_until)>=julianday(created_at)+365*7 THEN 1 ELSE 0 END) retention_marked,MAX(created_at) latest FROM audit").fetchone())
        triggers = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name IN ('audit_no_update','audit_no_delete')").fetchone()[0]
        latest_regression = db.execute("SELECT created_at,result FROM regression ORDER BY julianday(created_at) DESC,id DESC LIMIT 1").fetchone()
        versions = [dict(row) for row in db.execute("SELECT agent,MAX(version) version FROM prompt_versions GROUP BY agent")]
        previous = []
        if days:
            previous = db.execute("SELECT action,COUNT(*) count FROM audit WHERE action IN ('approve_send','discard') AND julianday(created_at)>=julianday(?) AND julianday(created_at)<julianday(?) GROUP BY action", ((start-timedelta(days=days)).isoformat(), start.isoformat())).fetchall()
    by_draft = {row["id"]: row for row in drafts}
    by_case = {row["id"]: row for row in cases}
    window_drafts = [row for row in drafts if start <= datetime.fromisoformat(row["created_at"]).astimezone(timezone.utc) <= end]
    scorecards = [obj(row["scorecard"]) for row in window_drafts]
    assessed = [score for score in scorecards if isinstance(score.get("passed"), bool)]
    tone_scores = [score["tone_score"] for score in scorecards if type(score.get("tone_score")) in (int, float) and 0 <= score["tone_score"] <= 100]
    matched_approvals = defaultdict(list)
    for row in approvals:
        draft_id = obj(row["payload"]).get("draft_id")
        if isinstance(draft_id, str):
            matched_approvals[(draft_id, row["case_id"])].append(row)
    human_signed = checked_outbox = false_check_failures = 0
    for row in outbox:
        matching = matched_approvals[(row["draft_id"], row["case_id"])]
        # Current account role is evidence, not a historical identity attestation.
        if any(roles.get(item["actor"]) in ("rm", "admin") and abs((datetime.fromisoformat(item["created_at"]) - datetime.fromisoformat(row["created_at"])).total_seconds()) <= 300 for item in matching):
            human_signed += 1
        draft = by_draft.get(row["draft_id"])
        check = obj(draft["scorecard"]).get("zero_false_chases") if draft else None
        if draft and draft["case_id"] == row["case_id"] and isinstance(check, bool):
            checked_outbox += 1
            false_check_failures += not check
    actions = Counter(row["action"] for row in audit)
    reviewed = actions["approve_send"] + actions["discard"]
    reason_count = sum(row["action"] == "discard" and bool(str(obj(row["payload"]).get("reason") or "").strip()) for row in audit)
    intercepts = Counter()
    initial_intercept_runs = set()
    qa_events = 0
    for row in events:
        data = obj(row["data"])
        if row["kind"] != "node_completed" or data.get("node") != "critique":
            continue
        card = data.get("scorecard")
        if not isinstance(card, dict) or not isinstance(card.get("passed"), bool):
            continue
        qa_events += 1
        if card["passed"] is False and data.get("iteration") == 1:
            initial_intercept_runs.add(row["run_id"])
        for key in ("zero_false_chases", "all_missing_consolidated", "no_prohibited_claims", "valid_email"):
            if card.get(key) is False:
                intercepts[key] += 1
        if card.get("policy_compliant") is False or (type(card.get("tone_score")) in (int,float) and card["tone_score"] < 95):
            intercepts["tone_policy"] += 1
    latest = {}
    for row in drafts:
        latest.setdefault(row["case_id"], row)
    exceptions = []
    for case in cases:
        reasons = []
        draft = latest.get(case["id"])
        if draft and draft["status"] in ("REVIEW", "BLOCKED"):
            if draft["gap_revision"] != case["revision"]:
                reasons.append("Checklist revision changed")
            card = obj(draft["scorecard"])
            if draft["status"] == "BLOCKED" or card.get("passed") is False:
                reasons.append("QA blocked")
            if not isinstance(card.get("passed"), bool):
                reasons.append("QA evidence unavailable")
        if case["nudge_due"]:
            reasons.append("Follow-up due")
        if reasons:
            exceptions.append({"case_id": case["id"], "jurisdiction": case["jurisdiction"], "issues": reasons})
    previous = {row["action"]: row["count"] for row in previous}
    previous_total = sum(previous.values())
    daily = defaultdict(lambda: {"approved": 0, "discarded": 0})
    for row in audit:
        if row["action"] in ("approve_send", "discard"):
            date = datetime.fromisoformat(row["created_at"]).astimezone(timezone.utc).date().isoformat()
            daily[date]["approved" if row["action"] == "approve_send" else "discarded"] += 1
    trend_start = max(start, end.replace(hour=0, minute=0, second=0,microsecond=0)-timedelta(days=89)) if days else end.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=29)
    trend = []
    date = trend_start.date()
    while date <= end.date():
        value = daily[date.isoformat()]
        total = value["approved"] + value["discarded"]
        trend.append({"date": date.isoformat(), **value, "discard_rate": value["discarded"]/total if total else None})
        date += timedelta(days=1)
    allowed_actions = {"draft_generated","draft_edited_and_rechecked","approve_send","discard","synthetic_document_received","client_reply_recorded","prompts_saved","mcp_approval_authorized"}
    recent = []
    for row in audit:
        if row["action"] not in allowed_actions:
            continue
        payload = obj(row["payload"])
        draft_id = payload.get("draft_id")
        draft = by_draft.get(draft_id) if isinstance(draft_id, str) else None
        score = obj(draft["scorecard"]).get("tone_score") if draft else None
        recent.append({"event_id": row["id"], "created_at": row["created_at"], "action": row["action"], "case_id": row["case_id"],
                       "jurisdiction": by_case.get(row["case_id"],{}).get("jurisdiction"), "actor_role": roles.get(row["actor"], "integration / unresolved"),
                       "tone_score": score if type(score) in (int,float) and 0 <= score <= 100 else None,
                       "reason_recorded": bool(str(payload.get("reason") or "").strip()) if row["action"] == "discard" else None})
        if len(recent) == 50:
            break
    regression = obj(latest_regression["result"]) if latest_regression else {}
    tests = regression.get("results")
    test_count = len(tests) if isinstance(tests, list) else 0
    gates = [
        {"name":"Identity & access", "status":"implemented", "detail":"Dedicated CRO/CFO read-only API scopes; operational writes remain role-gated."},
        {"name":"Data classification", "status":"scope limited", "detail":"Synthetic prototype records. Production data classification and on-prem boundaries are not verified here."},
        {"name":"Gateway & egress", "status":"not evidenced", "detail":"Provider outcomes are recorded; gateway rate limits, network egress and vendor retention terms are not attested."},
        {"name":"Tool sign-off", "status":"implemented", "detail":"Read-before-write, received-document exclusions and exact-draft RM/admin authorization are enforced by app logic."},
        {"name":"Model risk review", "status":"not evidenced", "detail":"The app prepares outreach, not AML/credit ratings. No formal MRM classification or exemption record is stored."},
        {"name":"Prompt change control", "status":"implemented", "detail":"Admin publishing requires an exact passing five-case regression less than one hour old; latest test is shown separately."},
        {"name":"Audit & retention", "status":"partial", "detail":f"{triggers}/2 append-only audit triggers present. Local retention dates do not prove durable seven-year storage or hash-chain integrity."},
        {"name":"Adoption & drift", "status":"partial", "detail":"Approval, edit and discard actions are stored. Dashboard thresholds are local review aids, not live alerts or a kill switch."},
    ]
    return {"period":{"days":days,"start":start.isoformat(),"end":end.isoformat(),"timezone":"UTC"},
            "metrics":{"outbox_records":len(outbox),"human_signed":human_signed,"signoff_coverage":human_signed/len(outbox) if outbox else None,
                       "outbox_check_assessed":checked_outbox,"outbox_check_failures":false_check_failures,"outbox_check_failure_rate":false_check_failures/checked_outbox if checked_outbox else None,
                       "missing_outbox_check_evidence":len(outbox)-checked_outbox,"review_actions":reviewed,"approved":actions["approve_send"],"discarded":actions["discard"],"edited":actions["draft_edited_and_rechecked"],
                       "discard_rate":actions["discard"]/reviewed if reviewed else None,"previous_discard_rate":previous.get("discard",0)/previous_total if previous_total else None,"previous_review_actions":previous_total,
                       "discard_reasons_recorded":reason_count,"drafts_created":len(window_drafts),"assessed_drafts":len(assessed),"qa_passed":sum(card["passed"] for card in assessed),"qa_failed":sum(not card["passed"] for card in assessed),
                       "average_tone_score":sum(tone_scores)/len(tone_scores) if tone_scores else None,"initial_intercepted_runs":len(initial_intercept_runs),"streamed_qa_evaluations":qa_events,
                       "rewrite_events":sum(row["kind"]=="revision" for row in events),"case_inventory":len(cases),"documents":documents,"workflow_runs":runs},
            "intercepts":dict(intercepts),"daily":trend,"gates":gates,"providers":providers,"exceptions":exceptions[:50],"exception_count":len(exceptions),
            "regions":{region:{"cases":sum(case["jurisdiction"]==region for case in cases),"exceptions":sum(row["jurisdiction"]==region for row in exceptions)} for region in ("UK","SG","US")},
            "audit":recent,"audit_coverage":{**audit_coverage,"append_only_triggers":triggers},
            "change_control":{"latest_test_at":latest_regression["created_at"] if latest_regression else None,"latest_test_passed":regression.get("passed") if isinstance(regression.get("passed"),bool) else None,"latest_test_cases":test_count,"prompt_versions":versions},
            "limitations":["This is synthetic operational-control evidence, not an AML/credit risk rating, regulatory assurance or independent control audit.",
                           "Outbox check findings use the linked draft’s stored scorecard, not an independent replay against a historic document snapshot. Missing evidence is reported separately. No external email delivery exists in this prototype.",
                           "Human sign-off evidence matches case/draft IDs, an approval audit event within five minutes of the outbox timestamp, and the approver’s current RM/admin role. Historical role membership and identity-provider attestation are not stored.",
                           "QA draft metrics cover final stored scorecards for drafts created in the window. Intercepts come only from persisted streaming Critique events; older/nonstreaming executions may have no intermediate QA evidence. Failure categories can overlap.",
                           "Case exceptions, document inventory, prompt versions and latest regression are current snapshots. Review/action metrics use audit timestamps; runs use start dates. A latest test is not proof of which version was published.",
                           "Discard trend excludes days with no review actions. The comparison window is the preceding calendar window and may have different review volumes. All-history view has no prior-period comparison and shows the latest 30 trend days.",
                           "Audit payload text, client contacts, full drafts, prompts and secrets are excluded. Audit rows may outlive linked drafts. Instance-local SQLite can lose records on replacement; durable seven-year retention and cryptographic hash chaining are not implemented."]}
