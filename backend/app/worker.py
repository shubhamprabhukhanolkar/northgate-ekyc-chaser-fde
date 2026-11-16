import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from .db import connect, audit

logger = logging.getLogger("northgate")


def scan_nudges():
    cutoff = (datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
    with connect() as db:
        found = db.execute("SELECT id FROM cases WHERE last_sent_at <= ? AND replied_at IS NULL AND nudge_due=0 AND status='AWAITING_REPLY'", (cutoff,)).fetchall()
        for case in found:
            db.execute("UPDATE cases SET nudge_due=1 WHERE id=?", (case["id"],))
            audit(db, "worker", "nudge_flagged_for_rm", case["id"])
    if found:
        logger.info(json.dumps({"event": "nudge_scan", "flagged": len(found), "auto_send": False}))
    return len(found)


async def worker():
    while True:
        try:
            await asyncio.to_thread(scan_nudges)
        except Exception:
            logger.exception(json.dumps({"event": "worker_error"}))
        await asyncio.sleep(30)
