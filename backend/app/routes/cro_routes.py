from fastapi import APIRouter, Depends, HTTPException, Query
from ..auth import require
from ..risk import risk_summary

router = APIRouter(prefix="/api/cro", tags=["CRO risk oversight"])


@router.get("/summary")
def summary(days: int = Query(30, ge=0, le=90), user=Depends(require("cro", "admin"))):
    if days not in (0, 7, 30, 90):
        raise HTTPException(422, "Choose 7, 30 or 90 days, or 0 for all history")
    return risk_summary(days)
