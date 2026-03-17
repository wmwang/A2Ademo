# A2A Demo: Google ADK ↔ LangGraph

A minimal, runnable demo that proves **A2A (Agent-to-Agent) protocol** works —
two agents built on **completely different frameworks** communicate seamlessly
through the open A2A standard.

```
User query
  └─► [Google ADK Orchestrator]          ← framework 1
            │
            │  A2A Protocol  (HTTP JSON-RPC)
            │  /.well-known/agent.json
            │
            └─► [LangGraph Currency Agent]  ← framework 2
                      └─► Frankfurter API  (real-time FX rates)
```

## What is A2A?

[Agent2Agent (A2A)](https://a2a-protocol.org) is an open protocol (initiated
by Google, now under the Linux Foundation) that lets AI agents discover and
talk to each other regardless of their underlying framework, language, or host.
Think of it as "HTTP for agents": a standard transport so a LangGraph agent and
an ADK agent can collaborate without knowing each other's internals.

## Project structure

```
A2Ademo/
├── langgraph_agent/          # Framework 1: LangGraph + a2a-sdk
│   ├── agent.py              #   ReAct agent with currency tool
│   ├── agent_executor.py     #   A2A executor adapter (a2a-sdk)
│   └── __main__.py           #   A2A HTTP server  (port 10001)
│
├── adk_agent/                # Framework 2: Google ADK
│   ├── agent.py              #   LlmAgent + RemoteA2aAgent sub-agent
│   └── __main__.py           #   ADK runner (sends query, prints result)
│
├── run_demo.sh               # One-shot demo script
├── pyproject.toml
└── .env.example
```

## Quick start

### 1. Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or `pip`
- A [Google API key](https://aistudio.google.com/apikey) (free tier works)

### 2. Install dependencies

```bash
# with uv (recommended)
uv sync

# or with pip
pip install -e .
```

### 3. Configure

```bash
cp .env.example .env
# edit .env and set GOOGLE_API_KEY=...
```

### 4. Run the demo

```bash
bash run_demo.sh
# or with a custom question:
bash run_demo.sh "Convert 1000 TWD to USD and EUR"
```

The script will:
1. Start the **LangGraph agent** as an A2A HTTP server on port 10001
2. Print the auto-generated **Agent Card** (how ADK discovers it)
3. Start the **ADK orchestrator**, which routes the query to LangGraph via A2A
4. Print the final answer — pulled from real-time FX data

### 5. Run each side manually

```bash
# Terminal 1 — start the LangGraph A2A server
python -m langgraph_agent

# Terminal 2 — run the ADK orchestrator
python -m adk_agent "How much is 100 USD in EUR?"
```

## How A2A works here (step by step)

| Step | What happens |
|------|-------------|
| 1 | LangGraph agent starts; `a2a-sdk` serves an **Agent Card** at `/.well-known/agent.json` |
| 2 | ADK reads the Agent Card → discovers capabilities & endpoint |
| 3 | ADK sends `tasks/send` JSON-RPC call (A2A protocol) |
| 4 | LangGraph agent processes the request with its ReAct graph + Frankfurter API |
| 5 | Streaming updates flow back via A2A (`TaskState.working` → artifact) |
| 6 | ADK orchestrator receives the result and presents it to the user |

## Key A2A concepts shown

- **Agent Card** — machine-readable description of an agent's skills & endpoint
- **Task lifecycle** — `working` → `completed` state transitions
- **Streaming** — intermediate status messages via SSE
- **Framework opacity** — ADK has zero knowledge of LangGraph internals

## References

- [A2A Protocol spec](https://a2a-protocol.org/latest/)
- [a2a-sdk on PyPI](https://pypi.org/project/a2a-sdk/)
- [Google ADK docs — A2A](https://google.github.io/adk-docs/a2a/)
- [a2a-samples (official)](https://github.com/a2aproject/a2a-samples)
