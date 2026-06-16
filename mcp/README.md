# RRI Orchestrator — LangGraph + MCP Multi-Agent State Machine

A **deterministic, cyclic multi-agent orchestrator** built on **LangGraph** state
machines and the **Model Context Protocol (MCP)** for decoupled, secure tool
execution. It re-architects the agent loop from [`rri_orchestrator`](https://github.com/shahzeb-jadoon/rri_orchestrator)
(the production FastAPI/LiteLLM platform) onto an explicit, inspectable graph.

> **Status: working scaffold / reference implementation.** The graph, the
> self-consistency risk gate, the Human-in-the-Loop interrupt, and a real MCP
> SQLite tool server all run and are covered by tests. It is *not yet* wired to
> the full production backend — that integration is the next step. (No fabricated
> claims: what's described here is what's in the repo.)

## Architecture

```mermaid
graph TD
    START([User input]) --> SUP[Supervisor]
    SUP -->|route = tool| TOOL[MCP Tool node]
    TOOL --> SUP
    SUP -->|route = answer| RISK[Risk eval<br/>self-consistency variance]
    RISK -->|risk &lt;= threshold| GEN[Generator]
    RISK -->|risk &gt; threshold| HITL[Human-in-the-Loop<br/>interrupt + resume]
    HITL --> GEN
    GEN --> END([Final answer])
```

The Supervisor ↔ MCP-Tool loop makes this a genuine **cyclic** graph (LangGraph
supports cycles — this is deliberately **not** a DAG).

## Why these pieces

- **LangGraph** — one typed, reducer-backed `AgentState` shared across nodes, with
  explicit routing, a real tool-use cycle, and durable checkpoints that make
  Human-in-the-Loop `interrupt()` / `resume` possible.
- **MCP** — tools (here, a SQLite interaction-history store) live behind a
  Model Context Protocol server, so the reasoning engine is decoupled from
  execution and tools are swappable/sandboxable.
- **Self-consistency risk gate** — instead of trusting one draft, the risk node
  samples several and measures their disagreement (token-level variance). High
  disagreement routes to a human. This is the honest version of a "treat the
  output as a distribution with a variance budget" mindset — a real uncertainty
  proxy, *not* "actuarial survival modelling."

## Layout

```
rri-orchestrator-mcp/
├── src/rri_mcp/
│   ├── state.py        # typed AgentState (additive reducers)
│   ├── llm.py          # tiny LiteLLM wrapper (mockable)
│   ├── risk.py         # self-consistency disagreement scorer
│   ├── graph.py        # the LangGraph state machine (build_graph)
│   └── mcp_client.py   # MCP stdio client -> sync ToolFn adapter
├── mcp_servers/
│   └── sqlite_server.py   # real FastMCP server exposing query_interaction_history
├── tests/              # offline tests (fakes) for risk + graph + HITL
├── pyproject.toml
└── .github/workflows/ci.yml
```

## Quick start

```bash
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -e ".[dev]"
pytest -q                                          # all tests run offline

# Try the MCP server standalone:
python mcp_servers/sqlite_server.py
```

Run the graph with real models (needs an API key in your env, e.g. `OPENAI_API_KEY`):

```python
from rri_mcp import build_graph
from rri_mcp.mcp_client import make_mcp_query

app = build_graph(mcp_query=make_mcp_query())
out = app.invoke(
    {"messages": [{"role": "user", "content": "Check the interaction history and advise robot A."}],
     "risk_threshold": 0.5},
    config={"configurable": {"thread_id": "demo"}},
)
print(out["messages"][-1]["content"])
```

## PostgreSQL MCP server

A production-leaning MCP server (`mcp_servers/postgres_server.py`) exposes the same
`query_interaction_history` tool against PostgreSQL instead of demo SQLite. Values
are parameterized; table/column identifiers are allow-listed (`sql_safety.py`).

```bash
pip install -e ".[postgres]"
$env:DATABASE_URL = "postgresql://user:pass@host:5432/rri"   # PowerShell
python mcp_servers/postgres_server.py
```

Point the graph at it the same way: `make_mcp_query("mcp_servers/postgres_server.py")`.

## Roadmap

- [x] PostgreSQL-backed MCP server (env-driven, parameterized, identifier allow-listing).
- [ ] Point it at the **live rri_orchestrator schema** and deploy alongside the platform.
- [ ] Add a Docker-isolated code-interpreter MCP server.
- [ ] Prometheus/Grafana telemetry on routing latency + token usage.
- [ ] Publish the eval/risk micro-study (variance-vs-accuracy on a prompt suite).
