import re
from .common import call


def deterministic_score(draft, checklist):
    text = (str(draft.get("subject", "")) + " " + str(draft.get("body", ""))).casefold()
    missing = {d["id"] for d in checklist["missing"]}
    received = {d["id"] for d in checklist["received"]}
    requested = draft.get("requested_document_ids", [])
    valid_ids = isinstance(requested, list) and all(isinstance(x, str) for x in requested)
    requested = set(requested) if valid_ids else set()
    # Exact names are required in generated and edited emails, which also prevents omissions.
    false_chases = [d["name"] for d in checklist["received"] if d["name"].casefold() in text]
    prohibited = bool(re.search(r"\b(low|medium|high)[ -]risk\b|risk rat(e|ing)|authentic|forged|fraudulent|genuine|verified documents?|documents? (are |is )?valid", text))
    return {"zero_false_chases": not false_chases and not (requested & received),
            "all_missing_consolidated": valid_ids and requested == missing and all(d["name"].casefold() in text for d in checklist["missing"]),
            "no_prohibited_claims": not prohibited,
            "valid_email": isinstance(draft.get("body"), str) and 30 <= len(draft["body"]) <= 20000 and bool(draft.get("subject"))}


async def critique(state):
    rules = deterministic_score(state["draft"], state["checklist"])
    result, provider = await call(state, "critique", {"draft": state["draft"], "checklist": state["checklist"], "rules": rules},
                                  {"tone_score": 98, "policy_compliant": True, "feedback": []})
    score = result.get("tone_score", 0)
    tone_ok = isinstance(score, (int, float)) and 95 <= score <= 100 and result.get("policy_compliant") is True
    feedback = [name for name, passed in rules.items() if not passed]
    if not tone_ok:
        feedback.append("Tone and policy must score at least 95%")
    feedback.extend(str(x) for x in result.get("feedback", [])[:10])
    scorecard = {**rules, "tone_score": score, "policy_compliant": result.get("policy_compliant") is True,
                 "passed": all(rules.values()) and tone_ok, "feedback": feedback, "iterations": state.get("attempts", 1)}
    return {"scorecard": scorecard, "feedback": feedback, "provider": provider}
