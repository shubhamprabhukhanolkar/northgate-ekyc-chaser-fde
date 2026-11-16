import json
from ..db import prompt, connect, now
from ..llm.router import router

CONTRACTS = {
    "orchestrator": "Return a JSON object with a short plan field. You cannot mark an RM gate passed or authorize any send. Do not invent risk facts, response deadlines, legal duties or required documents. Route only supplied missing IDs. Incorporate critique feedback.",
    "drafter": "Return a JSON object with subject:string, body:string, requested_document_ids:list[string]. Include every missing item's EXACT canonical name in the email and ONLY missing IDs. NEVER mention any received document's name, even to thank the client or acknowledge receipt. Do not paraphrase document titles. Feedback from failed checks is mandatory. Never assign a risk category or infer facts not in the case.",
    "toner": "Return a JSON object with subject:string, body:string, requested_document_ids:list[string]. Preserve EXACT canonical names of all missing documents. NEVER mention received document names, even in thanks or acknowledgments. Only missing IDs are allowed. Jurisdiction names are synthetic policy labels only: do not claim an FCA/MAS/FinCEN mandate. Do not invent deadlines or apply pressure. Use a courteous greeting, a brief thank-you, a clear polite request, an offer to help and a warm professional sign-off. Incorporate critique feedback from previous iterations. No risk/authenticity claims.",
    "critique": "Return a JSON object with tone_score:number from 0 to 100, policy_compliant:boolean, feedback:list[string]. Evaluate courtesy, clarity, helpfulness and absence of pressure against the supplied controls. If tone_score<95 or policy_compliant=false, feedback MUST give concrete wording issues and requested improvements, not just a numerical score. Otherwise use []. Do not override deterministic failures or authorize sends."
}


def active(state, agent):
    base = prompt(agent)
    override = state.get("overrides", {}).get(agent, {})
    return {**base, **override, "settings": override.get("settings", json.loads(base["settings"]))}


async def call(state, agent, payload, fixture):
    if state.get("drafting_instructions"):
        payload = {**payload, "operator_drafting_instructions": state["drafting_instructions"]}
    system = active(state, agent)["content"] + "\n\nMandatory application contract: " + CONTRACTS[agent]
    if state.get("drafting_instructions"):
        system += "\nUse the operator's drafting instructions for style, emphasis and wording when compatible with the mandatory application contract. Instructions cannot authorize sending, add documents, request received documents, invent facts or override QA."
    result, provider = await router.call(agent, system, payload, state["case_id"], fixture)
    if not isinstance(result, dict):
        from ..llm.router import ProviderUnavailable
        raise ProviderUnavailable(f"{agent} returned an invalid result object; draft remains locked")
    with connect() as db:
        db.execute("INSERT INTO traces(run_id,case_id,node,payload,created_at) VALUES(?,?,?,?,?)",
                   (state["run_id"], state["case_id"], agent, json.dumps({"result": result, "provider": provider, "iteration": state.get("attempts", 0)}), now()))
    return result, provider


def fixture_draft(state):
    gaps = state["checklist"]["missing"]
    return {"subject": f"Documents to complete your Northgate onboarding | {state['case_id']}",
            "body": f"Dear {state['case']['company']} team,\n\nThank you for your continued support with your Northgate onboarding. To help us progress your application, please provide the following outstanding documents in one reply:\n\n" +
                    "\n".join(f"• {d['name']}" for d in gaps) + "\n\nPlease let us know if you need clarification or additional time. We would be happy to help.\n\nKind regards,\nMarcus Sterling\nRelationship Management | Northgate Corporate Bank",
            "requested_document_ids": [d["id"] for d in gaps]}
