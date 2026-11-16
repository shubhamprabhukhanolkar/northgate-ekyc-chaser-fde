import json
from unittest.mock import AsyncMock
import pytest
from app.config import settings
from app.db import rows
from app.llm.router import LLMRouter, ProviderUnavailable


@pytest.mark.parametrize("failure", [TimeoutError(), ProviderUnavailable("quota exhausted")])
async def test_gemini_groq_failover(monkeypatch, failure):
    settings().offline_demo = False
    router = LLMRouter()
    monkeypatch.setattr(router, "gemini", AsyncMock(side_effect=failure))
    monkeypatch.setattr(router, "groq", AsyncMock(return_value=(json.dumps({"ok": True}), 120, 40)))
    result, provider = await router.call("drafter", "system", {}, "test-case")
    assert provider == "groq" and result["ok"]
    ledger = rows("SELECT * FROM cost_ledger ORDER BY id")
    assert len(ledger) == 2
    assert ledger[0]["status"] == "error"
    assert ledger[1]["failover"] == 1 and ledger[1]["cost_usd"] > 0
    assert ledger[1]["prompt_tokens"] == 120


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_retryable_http_statuses(monkeypatch, status):
    settings().offline_demo = False
    class Failure(Exception):
        status_code = status
    router = LLMRouter()
    monkeypatch.setattr(router, "gemini", AsyncMock(side_effect=Failure()))
    monkeypatch.setattr(router, "groq", AsyncMock(return_value=('{"ok":true}', 10, 5)))
    assert (await router.call("test", "system", {}))[1] == "groq"


async def test_both_providers_fail_without_fake_draft(monkeypatch):
    settings().offline_demo = False
    router = LLMRouter()
    monkeypatch.setattr(router, "gemini", AsyncMock(side_effect=TimeoutError()))
    monkeypatch.setattr(router, "groq", AsyncMock(side_effect=TimeoutError()))
    with pytest.raises(ProviderUnavailable):
        await router.call("test", "system", {})
    assert len(rows("SELECT * FROM cost_ledger WHERE status='error'")) == 2


async def test_invalid_json_still_records_billed_usage(monkeypatch):
    settings().offline_demo = False
    router = LLMRouter()
    monkeypatch.setattr(router, "gemini", AsyncMock(return_value=('not json', 100, 10)))
    with pytest.raises(ProviderUnavailable):
        await router.call("test", "system", {})
    assert rows("SELECT * FROM cost_ledger")[0]["prompt_tokens"] == 100
