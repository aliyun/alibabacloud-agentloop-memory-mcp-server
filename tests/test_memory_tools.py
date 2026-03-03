"""
Integration tests for AgentLoop Memory MCP Server.

Uses the MCP SDK client to connect via SSE and exercise all 5 tools.
Requires environment variables to be set (skips otherwise).

Usage:
    pytest tests/test_memory_tools.py -v
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time

import httpx
import pytest

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SERVER_HOST = "127.0.0.1"
SERVER_PORT = int(os.getenv("TEST_MCP_PORT", "18765"))
TEST_USER_ID = "integration_test_user"
TEST_CLIENT_NAME = "integration_test_client"
SSE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/mcp/{TEST_CLIENT_NAME}/sse/{TEST_USER_ID}"

REQUIRED_ENVS = [
    "ALIBABA_CLOUD_ACCESS_KEY_ID",
    "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    "ALIBABA_CLOUD_WORKSPACE",
    "ALIBABA_CLOUD_MEMORY_STORE",
]


def _missing_envs() -> list[str]:
    return [e for e in REQUIRED_ENVS if not os.getenv(e)]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def server_process():
    missing = _missing_envs()
    if missing:
        pytest.skip(f"Missing env vars: {', '.join(missing)}")

    env = os.environ.copy()
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "mcp_server_agentloop_memory",
            "--port", str(SERVER_PORT),
            "--host", SERVER_HOST,
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://{SERVER_HOST}:{SERVER_PORT}/docs", timeout=2.0)
            if r.status_code == 200:
                break
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(1)
    else:
        proc.kill()
        proc.wait()
        pytest.fail("Server did not start within 20s")

    yield proc

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _extract_text(result) -> str:
    if result and result.content:
        for block in result.content:
            if hasattr(block, "text"):
                return block.text
    return str(result)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_memory_lifecycle(server_process):
    """E2E test: add -> wait -> search -> list -> delete by id -> delete all."""
    from mcp.client.sse import sse_client
    from mcp.client.session import ClientSession

    async with sse_client(SSE_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init_result = await session.initialize()
            assert init_result.serverInfo is not None

            # List tools
            tools_result = await session.list_tools()
            tool_names = {t.name for t in tools_result.tools}
            expected = {"add_memories", "search_memory", "list_memories", "delete_memories", "delete_all_memories"}
            assert expected <= tool_names, f"Missing tools: {expected - tool_names}"

            # Cleanup
            await session.call_tool("delete_all_memories", {})

            # Add memories
            test_texts = [
                "I live in Hangzhou, love running by West Lake",
                "I am allergic to seafood, especially shrimp",
                "I use Python and VS Code for daily work",
            ]
            for text in test_texts:
                result = await session.call_tool("add_memories", {"text": text})
                text_result = _extract_text(result)
                assert "Error" not in text_result, f"add_memories failed: {text_result}"

            # Wait for async memory extraction
            await asyncio.sleep(120)

            # Search
            result = await session.call_tool("search_memory", {"query": "where do I live"})
            text_result = _extract_text(result)
            parsed = json.loads(text_result)
            assert len(parsed.get("results", [])) > 0, "search_memory returned no results"

            # List
            result = await session.call_tool("list_memories", {})
            text_result = _extract_text(result)
            parsed = json.loads(text_result)
            memories = parsed.get("results", [])
            assert len(memories) > 0, "list_memories returned no results"

            # Delete by ID
            target_id = memories[0]["id"]
            result = await session.call_tool("delete_memories", {"memory_ids": [target_id]})
            text_result = _extract_text(result)
            assert "Successfully deleted 1/1" in text_result

            # Delete all
            result = await session.call_tool("delete_all_memories", {})
            text_result = _extract_text(result)
            assert "Successfully deleted all" in text_result


@pytest.mark.asyncio
async def test_tool_listing(server_process):
    """Verify all 5 tools are registered with correct names."""
    from mcp.client.sse import sse_client
    from mcp.client.session import ClientSession

    async with sse_client(SSE_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = {t.name for t in tools_result.tools}
            assert tool_names == {
                "add_memories",
                "search_memory",
                "list_memories",
                "delete_memories",
                "delete_all_memories",
            }
