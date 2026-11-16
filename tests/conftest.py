import pytest
from app.config import settings
from app.db import initialize
from app.services import case_locks


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "northgate.db"))
    monkeypatch.setenv("OFFLINE_DEMO", "true")
    monkeypatch.setenv("AUTH_SECRET", "test-session-secret-with-sufficient-entropy-1234567890")
    monkeypatch.setenv("MCP_API_KEY", "test-mcp-key")
    settings.cache_clear()
    case_locks.clear()
    initialize()
    yield
    settings.cache_clear()
