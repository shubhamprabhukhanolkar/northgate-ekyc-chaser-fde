from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..auth import current_user, require
from ..db import connect, audit, config
from ..config import settings
from ..services import finops

router = APIRouter(prefix="/api", tags=["finops"])


@router.get("/finops")
def summary(user=Depends(current_user)):
    return finops()


@router.get("/runtime")
def runtime(user=Depends(current_user)):
    cfg = settings()
    return {"offline_demo": cfg.offline_demo, "gemini_configured": bool(cfg.gemini_api_key), "groq_configured": bool(cfg.groq_api_key), "simulate_outage": config("simulate_outage") == "true", "gemini_model": cfg.gemini_model, "groq_model": cfg.groq_model}


class Outage(BaseModel):
    enabled: bool


@router.put("/runtime/outage")
def outage(body: Outage, user=Depends(require("admin"))):
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO config VALUES('simulate_outage',?)", (str(body.enabled).lower(),))
        audit(db, user["email"], "simulate_outage", payload={"enabled": body.enabled})
    return {"enabled": body.enabled}
