"""
Google ADK Orchestrator Agent
==============================
A general-purpose fab assistant that routes lot / WIP questions to the
LangGraph Fab WIP Agent running on port 10001 — via the A2A protocol.

The ADK framework handles all A2A networking automatically through
RemoteA2aAgent; from the orchestrator's perspective it's just a sub-agent.
"""
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# ── RemoteA2aAgent: wraps the LangGraph A2A server as an ADK sub-agent ───────
# ADK fetches the agent card from /.well-known/agent.json to discover
# capabilities, then routes tasks over HTTP using the A2A protocol.
fab_wip_expert = RemoteA2aAgent(
    name="fab_wip_expert",
    description=(
        "A semiconductor fab WIP (Work-In-Process) expert powered by LangGraph + Gemini. "
        "Handles lot status queries, process history, and hold information. "
        "Delegate ALL fab lot / WIP questions here."
    ),
    agent_card="http://localhost:10001/.well-known/agent.json",
)

# ── Root orchestrator (Google ADK LlmAgent) ──────────────────────────────────
root_agent = LlmAgent(
    name="orchestrator",
    model="gemini-2.0-flash",
    description="A helpful fab assistant that orchestrates tasks across specialist agents.",
    instruction="""You are a helpful semiconductor fab assistant.

For any question about lot status, WIP, process history, hold lots, equipment,
or anything related to fab manufacturing tracking, transfer the task to the
'fab_wip_expert' sub-agent — it has direct access to the WIP system.

For everything else, answer directly.
""",
    sub_agents=[fab_wip_expert],
)
