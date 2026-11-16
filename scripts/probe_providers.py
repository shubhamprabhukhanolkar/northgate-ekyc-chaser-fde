import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"backend"))
from app.llm.router import router
from app.config import settings


async def main():
    for provider in ("gemini", "groq"):
        try:
            text, incoming, outgoing = await getattr(router, provider)("Return JSON with ok:true.", {"task": "connection verification, synthetic data only"})
            print(f"{provider}: connected; model={settings().gemini_model if provider=='gemini' else settings().groq_model}; tokens={incoming}/{outgoing}", flush=True)
        except Exception as exc:
            print(f"{provider}: failed; type={type(exc).__name__}; status={getattr(exc, 'status_code', getattr(exc, 'code', None))}", flush=True)
            if provider == "groq":
                # Groq's structured error describes model availability, without request headers.
                body = getattr(exc, "body", {})
                if isinstance(body, dict):
                    error = body.get("error", body)
                    print("groq error:", {k: error.get(k) for k in ("code", "type", "message") if k in error}, flush=True)
                from groq import AsyncGroq
                async with AsyncGroq(api_key=settings().groq_api_key) as client:
                    models = await client.models.list()
                    print("Available Groq models:", [m.id for m in models.data], flush=True)


asyncio.run(main())
