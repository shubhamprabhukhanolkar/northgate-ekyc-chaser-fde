from fastapi import APIRouter, Depends, HTTPException, Query
from ..auth import require
from ..finance import financial_summary

router = APIRouter(prefix="/api/cfo", tags=["CFO finance"])


@router.get("/summary")
def summary(days: int = Query(30, ge=0, le=90), user=Depends(require("cfo", "admin"))):
    if days not in (0, 7, 30, 90):
        raise HTTPException(422, "Choose a 7, 30 or 90 day window, or 0 for all history")
    return financial_summary(days)
