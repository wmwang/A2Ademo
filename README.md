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

## Demo 3: The Debate Room (54+ rounds)

Three agents with clashing personalities hold a structured meeting. They debate
any topic for **54+ rounds** (18 turns each), then deliver closing statements
and cast a vote to reach a final verdict.

```
User Topic
  └─► meeting_runner.py  (direct A2A HTTP client — no ADK needed)
            │
            │  Round-robin, 54 rounds minimum
            │
            ├── 😄  Alex  the Optimist    :10005  — sees boundless possibility
            ├── 😟  Riley the Pessimist   :10007  — finds the fatal flaw in everything
            └── 🧐  Morgan the Rationalist :10006  — only logic and evidence

            After 54 rounds:
            ├── Final closing statements (each agent)
            ├── Vote (1-10 agreement score per agent)
            └── Overall verdict + summary
```

```bash
bash run_debate_demo.sh
# or with a custom topic:
bash run_debate_demo.sh "Should remote work become the permanent default?"
bash run_debate_demo.sh --rounds 24 "Is crypto the future of finance?"
```

---

## Demo 4: Scrum Meeting Simulation

Eight A2A agents simulate a real cross-functional engineering meeting. They
review either a **local codebase** or a **GitHub repository URL**, debate what
should be improved, and then turn the discussion into **exactly 3 scrum
backlog tickets** for the next sprint.

Detailed Traditional Chinese manual:
- [SCRUM_MEETING_USER_MANUAL.md](./SCRUM_MEETING_USER_MANUAL.md)

```
Repository Path or GitHub URL
  └─► scrum_meeting_demo/meeting_runner.py
            │
            │  Direct A2A HTTP calls to 8 specialist agents
            │
            ├── [A] Ada    / Senior Architect      :10010
            ├── [P] Parker / Product Manager       :10011
            ├── [Q] Quinn  / QA Lead               :10012
            ├── [D] Devon  / Senior Developer      :10013
            ├── [U] Casey  / User Representative   :10014
            ├── [O] Sky    / DevOps Engineer       :10015
            ├── [S] Sage   / Security Engineer     :10016
            └── [M] Morgan / Scrum Master          :10017

            Output:
            ├── Multi-round meeting transcript
            ├── Final position from each role
            └── 3 scrum tickets with owner, AC, and DoD
```

```bash
bash run_scrum_meeting_demo.sh
# review the current repo:
bash run_scrum_meeting_demo.sh .
# review another local project:
bash run_scrum_meeting_demo.sh /path/to/other/repo
# review a public GitHub repo:
bash run_scrum_meeting_demo.sh https://github.com/owner/repo
# customize the discussion depth:
bash run_scrum_meeting_demo.sh --rounds 3 .
```

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
│   │   └── agent_executor.py #   Generic A2A executor (shared by Demo 2 & 3)
│   ├── architect_agent/      #   Designs Tech Spec  (port 10002)
│   ├── coder_agent/          #   Writes code        (port 10003)
│   ├── reviewer_agent/       #   Reviews code       (port 10004)
│   └── orchestrator/         #   ADK orchestrator
│
├── debate_demo/              # Demo 3 — 54-round personality debate
│   ├── optimist_agent/       #   Alex the Optimist    (port 10005)
│   ├── rationalist_agent/    #   Morgan the Rationalist (port 10006)
│   ├── pessimist_agent/      #   Riley the Pessimist  (port 10007)
│   └── meeting_runner.py     #   Direct A2A client orchestrator
│
├── scrum_meeting_demo/       # Demo 4 — 8-role engineering meeting
│   ├── senior_architect_agent/
│   ├── product_manager_agent/
│   ├── qa_lead_agent/
│   ├── senior_developer_agent/
│   ├── user_representative_agent/
│   ├── devops_agent/
│   ├── security_agent/
│   ├── scrum_master_agent/
│   ├── repo_context.py       #   Local/GitHub repo context loader
│   ├── roles.py              #   Role config and prompts
│   └── meeting_runner.py     #   Multi-round meeting + ticket synthesis
│
├── run_demo.sh               # Demo 1 launcher
├── run_coding_demo.sh        # Demo 2 launcher
├── run_debate_demo.sh        # Demo 3 launcher
├── run_scrum_meeting_demo.sh # Demo 4 launcher
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
# edit .env and set:
# - GOOGLE_API_KEY for Demo 1 / Demo 2
# - DEBATE_* or OPENAI_* compatible settings for Demo 3 / Demo 4
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

### 6. Run Demo 3 — The Debate Room

```bash
bash run_debate_demo.sh
# custom topic:
bash run_debate_demo.sh "Should remote work become the permanent default?"
# more rounds (default is 18 per agent = 54 total):
bash run_debate_demo.sh --rounds 24 "Is crypto the future of finance?"
```

The script will:
1. Start three personality agent servers (Optimist :10005, Pessimist :10007, Rationalist :10006)
2. Run `meeting_runner.py` which drives 54+ rounds of debate via direct A2A HTTP calls
3. Each agent receives the full conversation history on every turn
4. After all rounds: closing statements, vote (1-10), and overall verdict

### 7. Run Demo 4 — Scrum Meeting Simulation

```bash
bash run_scrum_meeting_demo.sh .
# another local repo:
bash run_scrum_meeting_demo.sh /path/to/repo
# public GitHub repo:
bash run_scrum_meeting_demo.sh https://github.com/owner/repo
# custom objective:
bash run_scrum_meeting_demo.sh --rounds 3 --objective "請找出最值得先做的三個改善項目" .
```

The script will:
1. Start eight A2A role agents (Architect, PM, QA, Senior Developer, User Representative, DevOps, Security, Scrum Master)
2. Build a repository context from either a local path or a GitHub URL
3. Run a multi-round engineering meeting where every role debates priorities
4. Ask the PM agent to synthesize the discussion into exactly 3 scrum tickets

### 8. Run each agent manually

```bash
# Demo 1
python -m langgraph_agent          # port 10001
python -m adk_agent "What is the status of lot LOT-2024-001?"

# Demo 2
python -m coding_demo.architect_agent   # port 10002
python -m coding_demo.coder_agent       # port 10003
python -m coding_demo.reviewer_agent    # port 10004
python -m coding_demo.orchestrator "Build a rate-limiter middleware"

# Demo 3
python -m debate_demo.optimist_agent       # port 10005
python -m debate_demo.pessimist_agent      # port 10007
python -m debate_demo.rationalist_agent    # port 10006
python -m debate_demo.meeting_runner "Will AI replace software engineers?"
python -m debate_demo.meeting_runner --rounds 20 "Is remote work here to stay?"

# Demo 4
python -m scrum_meeting_demo.senior_architect_agent      # port 10010
python -m scrum_meeting_demo.product_manager_agent       # port 10011
python -m scrum_meeting_demo.qa_lead_agent               # port 10012
python -m scrum_meeting_demo.senior_developer_agent      # port 10013
python -m scrum_meeting_demo.user_representative_agent   # port 10014
python -m scrum_meeting_demo.devops_agent                # port 10015
python -m scrum_meeting_demo.security_agent              # port 10016
python -m scrum_meeting_demo.scrum_master_agent          # port 10017
python -m scrum_meeting_demo .
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
