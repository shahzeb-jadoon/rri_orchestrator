"""Shared state for the LangGraph orchestrator.

The whole point of using LangGraph (vs. a plain chain) is a single, typed,
reducer-backed state object that every node reads and writes. `messages` uses an
additive reducer so nodes can append without clobbering history.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, Optional, TypedDict


class AgentState(TypedDict, total=False):
    """State passed between every node in the graph.

    Fields:
        messages:       running transcript; appended to (never overwritten).
        route:          supervisor's decision for the next hop ("tool" | "answer").
        tool_result:    last MCP tool output, if any.
        risk_score:     0.0-1.0 self-consistency variance for the drafted answer.
        risk_threshold: above this, we hand off to a human (HITL).
        needs_human:    set by the risk node; consumed by the conditional edge.
        turn:           supervisor loop counter (guards against infinite cycles).
    """

    messages: Annotated[list[dict], add]
    route: str
    tool_result: Optional[str]
    draft: Optional[str]
    risk_score: float
    risk_threshold: float
    needs_human: bool
    turn: Annotated[int, add]
