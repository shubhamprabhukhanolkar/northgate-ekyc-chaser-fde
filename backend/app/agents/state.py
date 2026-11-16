from typing import TypedDict, Any


class ChaseState(TypedDict, total=False):
    case_id: str
    run_id: str
    case: dict
    checklist: dict
    plan: dict
    draft: dict
    scorecard: dict
    feedback: list[str]
    attempts: int
    provider: str
    overrides: dict[str, Any]
    drafting_instructions: str
