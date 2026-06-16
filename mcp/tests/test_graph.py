"""End-to-end graph tests with injected fakes (no network, no API key, no MCP server).

Covers the three behaviours that make this a real LangGraph orchestrator:
  1. low-risk answers flow straight through to the generator;
  2. high-risk answers pause at a Human-in-the-Loop interrupt and then resume;
  3. the supervisor<->tool cycle actually fires when history is requested.
"""

import itertools

from langgraph.types import Command

from rri_mcp.graph import build_graph


def _cfg(thread_id):
    return {"configurable": {"thread_id": thread_id}}


def test_low_risk_completes_without_human():
    # Identical samples => 0.0 risk => no human review.
    constant_llm = lambda messages, model: "Proceed to waypoint 3."
    app = build_graph(llm=constant_llm, n_samples=5)

    out = app.invoke(
        {"messages": [{"role": "user", "content": "what should robot A do?"}], "risk_threshold": 0.5},
        config=_cfg("low"),
    )

    assert "__interrupt__" not in out
    assert out["risk_score"] == 0.0
    assert out["messages"][-1] == {"role": "assistant", "content": "Proceed to waypoint 3."}


def test_high_risk_triggers_and_resumes_human_in_the_loop():
    # Every sample differs => high risk => interrupt() pauses the graph.
    counter = itertools.count()
    varying_llm = lambda messages, model: f"totally different answer {next(counter)}"
    app = build_graph(llm=varying_llm, n_samples=5)

    paused = app.invoke(
        {"messages": [{"role": "user", "content": "what should robot A do?"}], "risk_threshold": 0.3},
        config=_cfg("high"),
    )
    assert "__interrupt__" in paused  # graph stopped at human_review

    resumed = app.invoke(Command(resume={"approved": True}), config=_cfg("high"))
    assert resumed["messages"][-1]["role"] == "assistant"
    assert any("human_decision" in m.get("content", "") for m in resumed["messages"])


def test_supervisor_tool_cycle_fires_on_history_request():
    calls = {"n": 0}

    def fake_mcp(query, limit):
        calls["n"] += 1
        return "robot_b: yielding right of way"

    app = build_graph(
        llm=lambda messages, model: "Based on history, hold position.",
        mcp_query=fake_mcp,
        n_samples=3,
    )

    out = app.invoke(
        {"messages": [{"role": "user", "content": "use the interaction history please"}], "risk_threshold": 0.9},
        config=_cfg("cycle"),
    )

    assert calls["n"] >= 1  # the MCP tool node ran (cycle executed)
    assert out["tool_result"] == "robot_b: yielding right of way"
    assert out["messages"][-1]["role"] == "assistant"
