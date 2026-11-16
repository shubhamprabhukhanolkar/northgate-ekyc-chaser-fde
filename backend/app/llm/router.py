import asyncio
import json
import time
from google import genai
from google.genai import types
from groq import AsyncGroq
from ..config import settings
from ..db import config, connect, now
from .pricing import price


class ProviderUnavailable(RuntimeError):
    pass


class LLMRouter:
    async def gemini(self, system, payload):
        cfg = settings()
        if not cfg.gemini_api_key:
            raise ProviderUnavailable("Gemini API key is not configured")
        async with genai.Client(api_key=cfg.gemini_api_key).aio as client:
            response = await client.models.generate_content(model=cfg.gemini_model, contents=json.dumps(payload),
                config=types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json", temperature=0.2))
        usage = response.usage_metadata
        return response.text, usage.prompt_token_count or 0, usage.candidates_token_count or 0

    async def groq(self, system, payload):
        cfg = settings()
        if not cfg.groq_api_key:
            raise ProviderUnavailable("Groq API key is not configured")
        async with AsyncGroq(api_key=cfg.groq_api_key, timeout=cfg.llm_timeout_seconds, max_retries=0) as client:
            response = await client.chat.completions.create(model=cfg.groq_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload)}],
                response_format={"type": "json_object"}, temperature=0.2,
                max_completion_tokens=2048,
                **({"reasoning_effort": "low"} if "gpt-oss" in cfg.groq_model else {}))
        return response.choices[0].message.content, response.usage.prompt_tokens, response.usage.completion_tokens

    def record(self, agent, provider, incoming, outgoing, latency, case_id, status, failover):
        usd, gbp = price(provider, incoming, outgoing)
        model = settings().gemini_model if provider == "gemini" else settings().groq_model if provider == "groq" else "deterministic-fixture"
        with connect() as db:
            db.execute("INSERT INTO cost_ledger(agent_name,provider,model,prompt_tokens,completion_tokens,latency_ms,cost_usd,cost_gbp,case_id,created_at,status,failover) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (agent, provider, model, incoming, outgoing, latency, usd, gbp, case_id, now(), status, failover))

    async def call(self, agent, system, payload, case_id=None, fixture=None):
        if settings().offline_demo:
            if fixture is None:
                raise ProviderUnavailable("No offline fixture for this action")
            self.record(agent, "offline_demo", 0, 0, 0, case_id, "fixture", 0)
            return fixture, "offline_demo"
        for index, provider in enumerate(("gemini", "groq")):
            started = time.perf_counter()
            try:
                if provider == "gemini" and config("simulate_outage") == "true":
                    raise ProviderUnavailable("Simulated Gemini outage")
                content, incoming, outgoing = await asyncio.wait_for(getattr(self, provider)(system, payload), settings().llm_timeout_seconds)
            except Exception as exc:
                self.record(agent, provider, 0, 0, (time.perf_counter()-started)*1000, case_id, "error", 0)
                status = getattr(exc, "status_code", getattr(exc, "code", None))
                recoverable = isinstance(exc, (ProviderUnavailable, TimeoutError, ConnectionError)) or status == 429 or (isinstance(status, int) and status >= 500) or any(x in type(exc).__name__.lower() for x in ("timeout", "connection", "ratelimit"))
                if provider == "groq" or not recoverable:
                    raise ProviderUnavailable(f"{provider} failed ({type(exc).__name__}); no draft approved") from exc
                continue
            # Record billed usage even when the model emits invalid JSON.
            self.record(agent, provider, incoming, outgoing, (time.perf_counter()-started)*1000, case_id, "success", index)
            try:
                return json.loads(content), provider
            except (ValueError, TypeError) as exc:
                raise ProviderUnavailable("Provider returned invalid JSON; draft remains locked") from exc
        raise ProviderUnavailable("Both providers unavailable")


router = LLMRouter()
