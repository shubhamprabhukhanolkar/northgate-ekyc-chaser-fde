"""Live outage drill; always restores normal routing. Never approves a draft."""
from pathlib import Path
import sys
import httpx
from dotenv import dotenv_values

values = dotenv_values(Path(__file__).resolve().parents[1]/".env")
base = sys.argv[1] if len(sys.argv)>1 else "http://127.0.0.1:8080"
with httpx.Client(base_url=base, timeout=180, follow_redirects=True) as client:
    client.post("/api/auth/login", json={"email": "admin@northgate.demo", "password": values.get("DEFAULT_OPERATOR_PASSWORD", "NorthgateDemo!2026")}).raise_for_status()
    before = client.get("/api/finops").json()["failovers"]
    client.put("/api/runtime/outage", json={"enabled": True}).raise_for_status()
    try:
        cid = "NG-2026-0842"
        client.get(f"/api/cases/{cid}").raise_for_status()
        response = client.post(f"/api/cases/{cid}/generate")
        response.raise_for_status()
        draft = response.json()
        assert draft["provider"] == "groq" and draft["scorecard"]["passed"], draft["scorecard"]
        after = client.get("/api/finops").json()["failovers"]
        assert after-before >= 4
        print("Live Gemini outage drill passed: Groq draft QA passed; successful failover calls:", after-before, flush=True)
    finally:
        client.put("/api/runtime/outage", json={"enabled": False}).raise_for_status()
        print("Normal Gemini-primary routing restored.", flush=True)
