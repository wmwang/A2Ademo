"""
Architect Agent
===============
A Senior Software Architect that designs system structure, defines interfaces,
and produces a clear tech spec for the Coder to implement.
"""
from typing import Any, AsyncIterable

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel


# ── Mock tools ────────────────────────────────────────────────────────────────

@tool
def list_design_patterns() -> list[dict]:
    """List common software design patterns with brief descriptions.

    Returns:
        A list of patterns with name and use-case descriptions.
    """
    return [
        {"pattern": "Repository", "use_case": "Abstract data access layer from business logic"},
        {"pattern": "Factory", "use_case": "Create objects without specifying concrete class"},
        {"pattern": "Strategy", "use_case": "Swap algorithms/behaviors at runtime"},
        {"pattern": "Observer", "use_case": "Event-driven, decoupled notification"},
        {"pattern": "Decorator", "use_case": "Extend behavior without subclassing"},
        {"pattern": "Singleton", "use_case": "Ensure single instance (e.g., config, DB conn)"},
        {"pattern": "Dependency Injection", "use_case": "Decouple components via interface injection"},
        {"pattern": "CQRS", "use_case": "Separate read and write models for scalability"},
    ]


@tool
def suggest_tech_stack(requirements: str) -> dict:
    """Suggest a technology stack based on feature requirements.

    Args:
        requirements: A description of the feature or system requirements.

    Returns:
        Recommended languages, frameworks, and libraries.
    """
    # Simple keyword-based mock
    req = requirements.lower()
    stack = {
        "language": "Python 3.11",
        "framework": "FastAPI" if "api" in req or "rest" in req or "http" in req else "Flask",
        "database": "PostgreSQL" if "persist" in req or "db" in req or "store" in req else "In-memory dict",
        "testing": "pytest + pytest-asyncio",
        "extras": [],
    }
    if "auth" in req or "token" in req:
        stack["extras"].append("python-jose (JWT)")
    if "async" in req or "concurrent" in req:
        stack["extras"].append("asyncio / anyio")
    if "cache" in req:
        stack["extras"].append("Redis / functools.lru_cache")
    return stack


# ── Response format ───────────────────────────────────────────────────────────

class ResponseFormat(BaseModel):
    status: str    # 'input_required' | 'completed' | 'error'
    message: str


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a Senior Software Architect with 15 years of experience.

Your job is to receive a feature request and produce a clear, actionable Tech Spec.

Use your tools to:
- list_design_patterns()     → choose the right patterns
- suggest_tech_stack()       → recommend technologies

Your Tech Spec must include:
1. **Overview** — one-paragraph summary of what will be built
2. **Components** — each component/module with its responsibility
3. **Interfaces** — function/class signatures and data contracts (types)
4. **Data Flow** — step-by-step flow from input to output
5. **Design Patterns** — which patterns you chose and why
6. **Tech Stack** — language, framework, libraries
7. **Edge Cases & Risks** — what could go wrong, how to handle it

Be concise but precise. The Coder will implement based solely on this spec.

Reply using ResponseFormat JSON:
- status: 'completed'      → spec is ready
- status: 'input_required' → need more detail from user
- status: 'error'          → unexpected problem
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class ArchitectAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
        self._graph = create_react_agent(
            model,
            tools=[list_design_patterns, suggest_tech_stack],
            checkpointer=MemorySaver(),
            prompt=SYSTEM_PROMPT,
            response_format=ResponseFormat,
        )

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        config = {"configurable": {"thread_id": session_id}}

        async for chunk in self._graph.astream(
            {"messages": [("human", query)]},
            config,
            stream_mode="values",
        ):
            last_msg = chunk["messages"][-1]

            if not isinstance(last_msg, AIMessage):
                continue

            if last_msg.tool_calls:
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Designing architecture...",
                }
                continue

            if hasattr(last_msg, "parsed") and last_msg.parsed:
                parsed: ResponseFormat = last_msg.parsed
                yield {
                    "is_task_complete": parsed.status == "completed",
                    "require_user_input": parsed.status == "input_required",
                    "content": parsed.message,
                }
                return

            if last_msg.content:
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": str(last_msg.content),
                }
