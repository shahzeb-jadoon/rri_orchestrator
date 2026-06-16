"""SQL identifier safety.

Table/column *names* cannot be passed as bound parameters, so when they come from
config (env vars) we must validate them ourselves. Values are always parameterized
elsewhere; this guards only identifiers. No third-party deps so it's trivially testable.
"""

from __future__ import annotations

import re

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_identifier(name: str) -> str:
    """Return `name` if it's a plain SQL identifier, else raise ValueError.

    Allows letters, digits, and underscores; must not start with a digit.
    Rejects quotes, whitespace, semicolons, dots, etc. — anything injectable.
    """
    if not isinstance(name, str) or not _IDENT_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return name
