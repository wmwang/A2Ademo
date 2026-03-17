"""
Google ADK Orchestrator Agent
==============================
A general-purpose assistant that routes currency-related questions to the
LangGraph Currency Agent running on port 10001 — via the A2A protocol.

The ADK framework handles all the A2A networking automatically through
RemoteA2aAgent; from the orchestrator's perspective it's just a sub-agent.
"""
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# ── RemoteA2aAgent: wraps the LangGraph A2A server as an ADK sub-agent ───────
# ADK will fetch the agent card from /.well-known/agent.json to discover
# capabilities, then route tasks to it over HTTP using the A2A protocol.
currency_expert = RemoteA2aAgent(
    name="currency_expert",
    description=(
        "A currency-exchange expert (powered by LangGraph + Gemini). "
        "Handles real-time exchange rates and currency conversions. "
        "Delegate ALL currency and forex questions here."
    ),
    agent_card="http://localhost:10001/.well-known/agent.json",
)

# ── Root orchestrator (Google ADK LlmAgent) ──────────────────────────────────
root_agent = LlmAgent(
    name="orchestrator",
    model="gemini-2.0-flash",
    description="A helpful assistant that orchestrates tasks across specialist agents.",
    instruction="""You are a helpful assistant.

For any question about currency exchange rates, currency conversion, or forex,
transfer the task to the 'currency_expert' sub-agent — it has real-time data.

For everything else, answer directly.
""",
    sub_agents=[currency_expert],
)
