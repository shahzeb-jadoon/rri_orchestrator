"""The LangGraph state machine.

This is a genuinely *cyclic* graph (NOT a DAG): the Supervisor and the MCP tool
node form a loop, so the agent can call tools repeatedly until it has enough
context, then draft an answer, risk-check it, and optionally pause for a human.

    START -> supervisor --(route="tool")--> mcp_tool --+
                  ^                                     |
                  +-------------------------------------+   (cycle)
             --(route="answer")--> risk_eval --(low risk)--> generator -> END
                                        |
                                   (high risk) -> human_review -> generator -> END

Everything external (LLM, MCP tool call) is injected, so the whole graph runs in
tests offline with fakes.
"""

from __future__ import annotations

from typing import Callable, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .llm import LLMFn, call_llm
from .risk import sample_and_score
from .state import AgentState

# A tool callable: (query, limit) -> result string. Wired to MCP in production
# (see mcp_servers/ + mcp_client.py); a fake is injected in tests.
ToolFn = Callable[[str, int], str]

MAX_TURNS = 3  # guard against an infinite supervisor<->tool cycle


def build_graph(
    llm: LLMFn = call_llm,
    mcp_query: Optional[ToolFn] = None,
    n_samples: int = 5,
    model: str = "gpt-4o-mini",
    checkpointer=None,
):
    """Compile and return the orchestrator graph.

    A checkpointer is required for Human-in-the-Loop `interrupt()` to work; we
    default to an in-memory one for convenience.
    """

    def supervisor(state):
        """Decide the next hop. Routes to a tool while more context is useful."""
        turn = state.get("turn", 0)
        last_user = next(
            (m["content"] for m in reversed(state["messages"]) if m.get("role") == "user"),
            "",
        )
        wants_history = any(k in last_user.lower() for k in ("history", "previous", "past", "earlier"))
        already_fetched = state.get("tool_result") is not None
        route = "tool" if (wants_history and not already_fetched and turn < MAX_TURNS) else "answer"
        return {"route": route, "turn": 1}  # turn uses an additive reducer

    def mcp_tool(state):
        """Execute a tool via MCP (injected). Loops back to the supervisor."""
        last_user = next(
            (m["content"] for m in reversed(state["messages"]) if m.get("role") == "user"),
            "",
        )
        result = mcp_query(last_user, 5) if mcp_query else ""
        return {
            "tool_result": result,
            "messages": [{"role": "tool", "content": result}],
        }

    def risk_eval(state):
        """Draft an answer from N samples and measure self-consistency variance."""
        draft, risk = sample_and_score(state["messages"], llm, n=n_samples, model=model)
        threshold = state.get("risk_threshold", 0.5)
        return {
            "draft": draft,
            "risk_score": risk,
            "needs_human": risk > threshold,
        }

    def human_review(state):
        """Pause the graph and surface the risky draft for a human decision.

        Execution stops here; resume with:
            graph.invoke(Command(resume={"approved": True}), config=...)
        """
        decision = interrupt(
            {
                "reason": "self-consistency risk above threshold",
                "risk_score": state["risk_score"],
                "draft": state.get("draft"),
            }
        )
        return {
            "needs_human": False,
            "messages": [{"role": "system", "content": f"human_decision={decision}"}],
        }

    def generator(state):
        """Finalize the answer (cheap path: return the vetted draft)."""
        final = state.get("draft") or llm(state["messages"], model)
        return {"messages": [{"role": "assistant", "content": final}]}

    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor)
    g.add_node("mcp_tool", mcp_tool)
    g.add_node("risk_eval", risk_eval)
    g.add_node("human_review", human_review)
    g.add_node("generator", generator)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        lambda s: s["route"],
        {"tool": "mcp_tool", "answer": "risk_eval"},
    )
    g.add_edge("mcp_tool", "supervisor")  # <-- the cycle
    g.add_conditional_edges(
        "risk_eval",
        lambda s: "human" if s["needs_human"] else "auto",
        {"human": "human_review", "auto": "generator"},
    )
    g.add_edge("human_review", "generator")
    g.add_edge("generator", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())
