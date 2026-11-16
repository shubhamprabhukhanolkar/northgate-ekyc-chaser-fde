import asyncio
import json
import time
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from ..auth import current_user, require
from ..db import rows
from .. import live

router = APIRouter(prefix="/api", tags=["live workflow"])


class DraftRequest(BaseModel):
    mode: Literal["auto", "guided"] = "auto"
    instructions: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def check_guidance(self):
        if self.mode == "guided" and len(self.instructions.strip()) < 5:
            raise ValueError("Please enter at least five characters of drafting instructions")
        return self


@router.post("/cases/{case_id}/runs", status_code=202)
async def start_run(case_id: str, body: DraftRequest = DraftRequest(), user=Depends(require("rm", "analyst", "admin"))):
    return live.start(case_id, user["email"], body.mode, body.instructions)


@router.get("/runs/latest")
def latest(case_id: str | None = None, user=Depends(current_user)):
    query = "SELECT * FROM workflow_runs" + (" WHERE case_id=?" if case_id else "") + " ORDER BY started_at DESC LIMIT 1"
    found = rows(query, (case_id,) if case_id else ())
    return found[0] if found else None


@router.get("/runs/{run_id}/events")
async def event_stream(run_id: str, request: Request, after: int = 0, user=Depends(current_user)):
    live.get_run(run_id)
    try:
        cursor = max(0, after, int(request.headers.get("last-event-id", "0")))
    except ValueError:
        cursor = max(0, after)

    async def stream():
        nonlocal cursor
        heartbeat = time.monotonic()
        yield "retry: 1500\n\n"
        while not await request.is_disconnected():
            batch = live.events(run_id, cursor)
            for event in batch:
                yield f"id: {event['id']}\nevent: workflow\ndata: {json.dumps(event)}\n\n"
                cursor = event["id"]
            if live.get_run(run_id)["status"] != "RUNNING" and not live.events(run_id, cursor):
                return
            if time.monotonic()-heartbeat > 12:
                yield ": heartbeat\n\n"
                heartbeat = time.monotonic()
            await asyncio.sleep(0.12)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})
