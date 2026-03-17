"""
Coding Orchestrator (Google ADK)
==================================
Coordinates three specialist A2A agents to handle a full feature development cycle:
  1. Architect Agent  → designs the Tech Spec
  2. Coder Agent      → implements the code from the spec
  3. Reviewer Agent   → audits the code and produces a review report
"""
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# ── Specialist sub-agents (each an independent A2A server) ───────────────────

architect = RemoteA2aAgent(
    name="architect",
    description=(
        "Senior Software Architect. Given a feature request, produces a detailed Tech Spec "
        "including components, interfaces, data flow, design patterns, and tech stack. "
        "Call this FIRST for any new feature."
    ),
    agent_card="http://localhost:10002/.well-known/agent.json",
)

coder = RemoteA2aAgent(
    name="coder",
    description=(
        "Senior Software Engineer. Given a Tech Spec, writes clean, production-quality "
        "Python code with type hints, docstrings, and error handling. "
        "Call this AFTER the architect has produced a spec."
    ),
    agent_card="http://localhost:10003/.well-known/agent.json",
)

reviewer = RemoteA2aAgent(
    name="reviewer",
    description=(
        "Senior Code Reviewer and QA Engineer. Given a Tech Spec and the Coder's implementation, "
        "audits the code for bugs, security issues, style problems, and missing tests. "
        "Call this AFTER the coder has produced code."
    ),
    agent_card="http://localhost:10004/.well-known/agent.json",
)

# ── Root orchestrator ─────────────────────────────────────────────────────────

root_agent = LlmAgent(
    name="coding_orchestrator",
    model="gemini-2.0-flash",
    description="Orchestrates a multi-agent software development pipeline.",
    instruction="""You are a Engineering Manager orchestrating a full software development cycle.

When a user gives you a feature request, follow this EXACT pipeline in order:

**Step 1 — Architecture**
Transfer the feature request to the 'architect' agent.
Tell it: "Design a Tech Spec for: <feature request>"
Wait for the Tech Spec.

**Step 2 — Implementation**
Transfer the Tech Spec to the 'coder' agent.
Tell it: "Implement the following Tech Spec:\n<tech spec from architect>"
Wait for the code.

**Step 3 — Review**
Transfer both the Tech Spec and the Code to the 'reviewer' agent.
Tell it: "Review this code against the spec.\n\nTech Spec:\n<spec>\n\nCode:\n<code>"
Wait for the review report.

**Step 4 — Final Summary**
Present the user with a clean summary:
- 📐 Tech Spec (from architect)
- 💻 Implementation (from coder)
- 🔍 Code Review (from reviewer)

Always complete all 3 steps before responding to the user.
Never skip a step or answer without running through the full pipeline.
""",
    sub_agents=[architect, coder, reviewer],
)
