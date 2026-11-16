import json
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..auth import current_user, require
from ..db import rows, prompt, connect, audit, now
from ..services import regression, prompt_digest

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class ToneSettings(BaseModel):
    formality: int = Field(ge=0, le=100)
    urgency: Literal["First Chase", "3-Day Nudge", "Escalation"]
    jurisdiction_clause: Literal["Auto", "UK FCA", "MAS Singapore", "US FinCEN"]


class PromptEdit(BaseModel):
    content: str = Field(min_length=20, max_length=12000)
    settings: ToneSettings


class Candidate(BaseModel):
    prompts: dict[Literal["orchestrator", "drafter", "toner", "critique"], PromptEdit]
    regression_id: str | None = None


def normalized(body):
    return {k: v.model_dump() for k, v in body.prompts.items()}


@router.get("")
def get_prompts(user=Depends(current_user)):
    return {"active": {a: {**prompt(a), "settings": json.loads(prompt(a)["settings"])} for a in ("orchestrator", "drafter", "toner", "critique")},
            "history": rows("SELECT id,agent,version,created_at,actor FROM prompt_versions ORDER BY id DESC LIMIT 40")}


@router.post("/test")
async def test(body: Candidate, user=Depends(require("admin"))):
    return await regression(normalized(body))


@router.put("")
def save(body: Candidate, user=Depends(require("admin"))):
    candidate = normalized(body)
    found = rows("SELECT * FROM regression WHERE id=?", (body.regression_id,))
    if not found or found[0]["digest"] != prompt_digest(candidate) or not json.loads(found[0]["result"])["passed"] or datetime.fromisoformat(found[0]["created_at"]) < datetime.now(timezone.utc)-timedelta(hours=1):
        raise HTTPException(409, "Run a passing five-case regression on these exact prompt settings before saving")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for agent, value in candidate.items():
            version = db.execute("SELECT MAX(version) FROM prompt_versions WHERE agent=?", (agent,)).fetchone()[0]+1
            db.execute("INSERT INTO prompt_versions(agent,content,settings,version,created_at,actor) VALUES(?,?,?,?,?,?)", (agent, value["content"], json.dumps(value["settings"]), version, now(), user["email"]))
        audit(db, user["email"], "prompts_saved", payload={"regression_id": body.regression_id})
    return {"saved": True}
