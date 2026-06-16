"""A real PostgreSQL-backed MCP server.

This is the production-leaning counterpart to sqlite_server.py: the same tool
(`query_interaction_history`), but reading from a PostgreSQL database — e.g. the
live rri_orchestrator store — instead of a demo SQLite file.

Configuration (env vars):
    DATABASE_URL   postgresql://user:pass@host:5432/dbname   (required)
    RRI_PG_TABLE   table to read from           (default: "messages")
    RRI_PG_TEXT    text/content column          (default: "content")
    RRI_PG_ORDER   ordering column (desc)        (default: "id")

Safety:
    - Values are always passed as bound parameters (no string interpolation).
    - Identifiers (table/column names) come from config and are allow-listed via
      sql_safety.safe_identifier before use.

Run standalone:
    set DATABASE_URL=postgresql://...   (PowerShell: $env:DATABASE_URL="...")
    python mcp_servers/postgres_server.py
"""

from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

# Make `src/` importable when run as a standalone script.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from rri_mcp.sql_safety import safe_identifier  # noqa: E402

mcp = FastMCP("rri-postgres")


def _conn():
    """Open a PostgreSQL connection from DATABASE_URL (psycopg imported lazily)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set; cannot connect to PostgreSQL.")
    import psycopg  # lazy: keeps the dep optional for offline unit tests

    return psycopg.connect(url)


@mcp.tool()
def query_interaction_history(query: str, limit: int = 5) -> str:
    """Return recent interaction rows whose text matches `query` (case-insensitive).

    Reads from the configured table/columns in PostgreSQL using a parameterized
    ILIKE search. Returns a friendly message on any error so the agent degrades
    gracefully instead of crashing the graph.
    """
    table = safe_identifier(os.environ.get("RRI_PG_TABLE", "messages"))
    text_col = safe_identifier(os.environ.get("RRI_PG_TEXT", "content"))
    order_col = safe_identifier(os.environ.get("RRI_PG_ORDER", "id"))
    limit = max(1, min(int(limit), 100))  # clamp

    sql = (
        f"SELECT {text_col} FROM {table} "
        f"WHERE {text_col} ILIKE %s "
        f"ORDER BY {order_col} DESC LIMIT %s"
    )
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute(sql, (f"%{query}%", limit))
            rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001 - surface a usable message to the agent
        return f"[postgres tool error] {type(exc).__name__}: {exc}"

    if not rows:
        return "No matching interactions."
    return "\n".join(str(r[0]) for r in rows)


if __name__ == "__main__":
    mcp.run()  # stdio transport
