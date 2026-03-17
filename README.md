# A2A Demo: Google ADK ↔ LangGraph

A minimal, runnable demo that proves **A2A (Agent-to-Agent) protocol** works —
two agents built on **completely different frameworks** communicate seamlessly
through the open A2A standard.

```
User query
  └─► [Google ADK Orchestrator]  (gpt-oss-120b)          ← framework 1
            │
            │  A2A Protocol  (HTTP JSON-RPC)
            │  /.well-known/agent.json
            │
            └─► [DeepAgents Fab WIP Agent]  (gpt-oss-120b)  ← framework 2
                      │
                      ├─ Planning      write_todos()  ← built-in task breakdown
                      ├─ Filesystem    read/write/edit_file()  ← context offload
                      │
                      ├─ Tools
                      │    ├─► get_lot_status()
                      │    ├─► get_lot_history()
                      │    └─► list_lots_on_hold()
                      │
                      └─► Mock WIP DB  (in-memory)
```

## What is A2A?

[Agent2Agent (A2A)](https://a2a-protocol.org) is an open protocol (initiated
by Google, now under the Linux Foundation) that lets AI agents discover and
talk to each other regardless of their underlying framework, language, or host.
Think of it as "HTTP for agents": a standard transport so a LangGraph agent and
an ADK agent can collaborate without knowing each other's internals.

---

## Demo 2: Multi-Agent Coding Pipeline

A second scenario that shows **multiple A2A agents collaborating** on a full
software development cycle, each playing a dedicated engineering role.

```
Feature Request
  └─► [ADK Coding Orchestrator]
            │
            │  A2A Protocol
            ├─────────────────► [Architect Agent]  :10002
            │                      list_design_patterns()
            │                      suggest_tech_stack()
            │                      └─► Tech Spec
            │
            ├─────────────────► [Coder Agent]  :10003
            │                      get_code_template()
            │                      └─► Implementation
            │
            └─────────────────► [Reviewer Agent]  :10004
                                   check_common_vulnerabilities()
                                   check_code_style()
                                   └─► Review Report
```

```bash
bash run_coding_demo.sh
# or with a custom feature request:
bash run_coding_demo.sh "Build a rate-limiter middleware for a FastAPI app"
```

---

## Project structure

```
A2Ademo/
├── langgraph_agent/          # Demo 1 — LangGraph Fab WIP agent
│   ├── agent.py              #   ReAct agent with WIP tools
│   ├── agent_executor.py     #   A2A executor adapter
│   └── __main__.py           #   A2A HTTP server  (port 10001)
│
├── adk_agent/                # Demo 1 — Google ADK orchestrator
│   ├── agent.py              #   LlmAgent + RemoteA2aAgent
│   └── __main__.py           #   ADK runner
│
├── coding_demo/              # Demo 2 — Multi-agent coding pipeline
│   ├── common/
│   │   └── agent_executor.py #   Generic A2A executor (shared)
│   ├── architect_agent/      #   Designs Tech Spec  (port 10002)
│   ├── coder_agent/          #   Writes code        (port 10003)
│   ├── reviewer_agent/       #   Reviews code       (port 10004)
│   └── orchestrator/         #   ADK orchestrator
│
├── run_demo.sh               # Demo 1 launcher
├── run_coding_demo.sh        # Demo 2 launcher
├── pyproject.toml
└── .env.example
```

## Quick start

### 1. Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or `pip`
- A `GOOGLE_API_KEY` for Gemini

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
# edit .env and set GOOGLE_API_KEY
```

### 4. Run Demo 1 — Fab WIP Query

```bash
bash run_demo.sh
# or with a custom question:
bash run_demo.sh "What is the status of lot LOT-2024-001?"
```

The script will:
1. Start the **LangGraph Fab WIP agent** as an A2A HTTP server on port 10001
2. Print the auto-generated **Agent Card** (how ADK discovers it)
3. Start the **ADK orchestrator**, which routes the query to LangGraph via A2A
4. Print the final answer — queried from the in-memory WIP database

### 5. Run Demo 2 — Multi-Agent Coding Pipeline

```bash
bash run_coding_demo.sh
# or with a custom feature request:
bash run_coding_demo.sh "Build a REST endpoint that returns a greeting"
```

The script will:
1. Start three specialist A2A servers (Architect :10002, Coder :10003, Reviewer :10004)
2. Run the ADK orchestrator, which drives the full pipeline:
   - Architect designs a Tech Spec
   - Coder implements code from the spec
   - Reviewer audits the code and produces a review report
3. Print the complete result (spec + code + review)

### 6. Run each agent manually

```bash
# Demo 1
python -m langgraph_agent          # port 10001
python -m adk_agent "What is the status of lot LOT-2024-001?"

# Demo 2
python -m coding_demo.architect_agent   # port 10002
python -m coding_demo.coder_agent       # port 10003
python -m coding_demo.reviewer_agent    # port 10004
python -m coding_demo.orchestrator "Build a rate-limiter middleware"
```

## How A2A works here (step by step)

| Step | What happens |
|------|-------------|
| 1 | Each specialist agent starts; `a2a-sdk` serves an **Agent Card** at `/.well-known/agent.json` |
| 2 | ADK reads each Agent Card → discovers capabilities & endpoint |
| 3 | ADK sends `tasks/send` JSON-RPC calls (A2A protocol) to each agent in sequence |
| 4 | Each agent processes its task using its own tools and LLM |
| 5 | Streaming updates flow back via A2A (`TaskState.working` → artifact) |
| 6 | ADK orchestrator assembles the final result from all three agents |

## Key A2A concepts shown

- **Agent Card** — machine-readable description of an agent's skills & endpoint
- **Task lifecycle** — `working` → `completed` state transitions
- **Streaming** — intermediate status messages via SSE
- **Framework opacity** — ADK orchestrates LangGraph agents without knowing their internals
- **Multi-agent coordination** — sequential pipeline where each agent's output feeds the next

## References

- [A2A Protocol spec](https://a2a-protocol.org/latest/)
- [a2a-sdk on PyPI](https://pypi.org/project/a2a-sdk/)
- [Google ADK docs — A2A](https://google.github.io/adk-docs/a2a/)
- [a2a-samples (official)](https://github.com/a2aproject/a2a-samples)
