import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_official_stdio_client_round_trip():
    root = Path(__file__).resolve().parents[1]
    server = StdioServerParameters(command=sys.executable,
        args=["-m", "app.mcp.server"],
        env={**os.environ, "PYTHONPATH": str(root/"backend"), "PYTHONIOENCODING": "utf-8"},
        cwd=str(root))
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "Northgate eKYC"
            tools = await session.list_tools()
            assert len(tools.tools) == 7
            result = await session.call_tool("list_onboarding_cases", {})
            assert not result.isError
            assert len(result.structuredContent["cases"]) == 42
            checklist = await session.call_tool("get_case_gap_checklist", {"case_id": "NG-2026-0841"})
            assert not checklist.isError
            assert checklist.structuredContent["received"]
            summary = await session.call_tool("get_finops_cost_summary", {})
            assert summary.structuredContent["roi"]["case_days_saved_monthly"] == 3000
