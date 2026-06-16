"""Unit tests for SQL identifier allow-listing (pure, offline)."""

import pytest

from rri_mcp.sql_safety import safe_identifier


def test_accepts_plain_identifiers():
    for ok in ("messages", "content", "interaction_history", "col_1", "_private"):
        assert safe_identifier(ok) == ok


def test_rejects_injection_attempts():
    for bad in (
        "messages; DROP TABLE users",
        "content OR 1=1",
        "tbl--",
        'a"b',
        "has space",
        "schema.table",
        "1col",
        "",
    ):
        with pytest.raises(ValueError):
            safe_identifier(bad)
