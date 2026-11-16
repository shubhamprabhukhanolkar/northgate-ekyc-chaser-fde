from fastapi import HTTPException
from ..db import rows, connect, now


def gap_check(case_id, actor=None):
    cases = rows("SELECT * FROM cases WHERE id=?", (case_id,))
    if not cases:
        raise HTTPException(404, "Case not found")
    docs = rows("SELECT * FROM documents WHERE case_id=? ORDER BY id", (case_id,))
    if actor:
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO read_receipts VALUES(?,?,?,?)", (actor, case_id, cases[0]["revision"], now()))
    return {"case": cases[0], "revision": cases[0]["revision"], "received": [d for d in docs if d["status"] == "RECEIVED"],
            "missing": [d for d in docs if d["status"] == "MISSING"], "source": "Synthetic On-Prem Document Store", "metadata_only": True}
