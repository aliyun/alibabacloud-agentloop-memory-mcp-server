"""
MCP client for testing an AgentLoop Memory MCP Server deployed on Alibaba Cloud FC.

Usage:
    python tests/test_client.py \
        --server-url "https://xxx/mcp/my_client/sse/my_user" \
        --token "your-bearer-token"
"""

import argparse
import asyncio
import json


def _extract_text(result) -> str:
    if result and result.content:
        for block in result.content:
            if hasattr(block, "text"):
                return block.text
    return str(result)


def _print_step(label: str):
    print(f"\n{'='*60}\n  {label}\n{'='*60}")


def _print_result(raw: str):
    try:
        parsed = json.loads(raw)
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    except (json.JSONDecodeError, TypeError):
        print(raw)


async def run(server_url: str, token: str):
    from mcp.client.sse import sse_client
    from mcp.client.session import ClientSession

    headers = {"Authorization": f"Bearer {token}"}

    print(f"Connecting to {server_url} ...")
    async with sse_client(url=server_url, headers=headers, sse_read_timeout=300) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init = await session.initialize()
            print(f"Connected. Server: {init.serverInfo.name}")

            # 1. List tools
            _print_step("list_tools")
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print(f"Available tools: {tool_names}")

            # 2. Clean up
            # _print_step("delete_all_memories (cleanup)")
            # result = await session.call_tool("delete_all_memories", {})
            # print(_extract_text(result))

            # 3. Add memories
            test_texts = [
                "我住在杭州，喜欢在西湖边跑步",
                "我对海鲜过敏，尤其是虾",
                "我日常使用 Python 和 VS Code 开发",
            ]
            for text in test_texts:
                _print_step(f"add_memories: {text}")
                result = await session.call_tool("add_memories", {"text": text})
                _print_result(_extract_text(result))

            # 4. Wait for async memory extraction
            wait_secs = 120
            print(f"\n⏳ Waiting {wait_secs}s for memory extraction ...")
            await asyncio.sleep(wait_secs)

            # 5. Search
            _print_step("search_memory: '我住在哪里'")
            result = await session.call_tool("search_memory", {"query": "我住在哪里"})
            _print_result(_extract_text(result))

            # 6. List
            _print_step("list_memories")
            result = await session.call_tool("list_memories", {})
            text_result = _extract_text(result)
            _print_result(text_result)

            # 7. Delete one by ID
            parsed = json.loads(text_result)
            memories = parsed.get("results", [])
            if memories:
                target_id = memories[0]["id"]
                _print_step(f"delete_memories: [{target_id}]")
                result = await session.call_tool("delete_memories", {"memory_ids": [target_id]})
                print(_extract_text(result))

            # 8. Delete all
            _print_step("delete_all_memories (final cleanup)")
            result = await session.call_tool("delete_all_memories", {})
            print(_extract_text(result))

            print(f"\n{'='*60}")
            print("  All tests passed!")
            print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Test an AgentLoop Memory MCP Server")
    parser.add_argument("--server-url", required=True, help="Full SSE endpoint URL, e.g. https://xxx/mcp/client/sse/user")
    parser.add_argument("--token", required=True, help="Bearer token for authentication")
    args = parser.parse_args()
    asyncio.run(run(args.server_url, args.token))


if __name__ == "__main__":
    main()
