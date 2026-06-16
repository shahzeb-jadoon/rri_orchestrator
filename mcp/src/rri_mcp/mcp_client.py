"""MCP client adapter: turns an MCP stdio tool into the sync `ToolFn` the graph wants.

The graph node calls `mcp_query(query, limit) -> str`. Under the hood this spins up
the MCP server over stdio, initializes a session, and calls the tool by name.
"""

from __future__ import annotations

import asyncio
from typing import Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _extract_text(result) -> str:
    """Pull plain text out of an MCP tool result (content is a list of blocks)."""
    parts = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


async def _acall(query: str, limit: int, server_script: str) -> str:
    params = StdioServerParameters(command="python", args=[server_script])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "query_interaction_history", {"query": query, "limit": limit}
            )
            return _extract_text(result)


def make_mcp_query(server_script: str = "mcp_servers/sqlite_server.py") -> Callable[[str, int], str]:
    """Return a sync `mcp_query(query, limit)` usable as the graph's ToolFn."""

    def mcp_query(query: str, limit: int = 5) -> str:
        return asyncio.run(_acall(query, limit, server_script))

    return mcp_query
