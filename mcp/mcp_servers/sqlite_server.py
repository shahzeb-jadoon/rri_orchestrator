"""A real Model Context Protocol (MCP) server exposing a SQLite tool.

This decouples tool execution from the LLM/agent: the graph never touches the DB
directly, it speaks MCP to this server. Run standalone for a quick check:

    python mcp_servers/sqlite_server.py

The graph talks to it through mcp_client.make_mcp_query() (stdio transport).
"""

from __future__ import annotations

import os
import sqlite3

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rri-sqlite")

DB_PATH = os.environ.get("RRI_DB", "rri_lab.db")


def _ensure_demo_db(path: str) -> None:
    """Create a tiny demo table so the tool returns something on first run."""
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS interactions "
        "(id INTEGER PRIMARY KEY, ts TEXT, speaker TEXT, content TEXT)"
    )
    if con.execute("SELECT COUNT(*) FROM interactions").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO interactions (ts, speaker, content) VALUES (?, ?, ?)",
            [
                ("2026-01-01T10:00", "robot_a", "Proceeding to waypoint 3."),
                ("2026-01-01T10:01", "robot_b", "Acknowledged, yielding right of way."),
            ],
        )
    con.commit()
    con.close()


@mcp.tool()
def query_interaction_history(query: str, limit: int = 5) -> str:
    """Return recent robot-robot interaction rows matching `query` (LIKE search)."""
    _ensure_demo_db(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT ts, speaker, content FROM interactions "
            "WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", int(limit)),
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return "No matching interactions."
    return "\n".join(f"[{ts}] {speaker}: {content}" for ts, speaker, content in rows)


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
