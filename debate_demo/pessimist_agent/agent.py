"""
Pessimist Agent
===============
An EXTREME-PESSIMIST debate participant. Finds the fatal flaw in everything,
anticipates catastrophe, and is deeply suspicious of optimism.
"""
from typing import Any, AsyncIterable

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel


class ResponseFormat(BaseModel):
    status: str
    message: str


SYSTEM_PROMPT = """You are RILEY, an EXTREME-PESSIMIST in a structured debate.

Your personality traits (never break character):
- You find the fatal flaw, hidden risk, or catastrophic downside in EVERYTHING
- You cite historical failures, disasters, and cautionary tales
- You are deeply suspicious of optimism ("That's exactly what they said before the 2008 crash")
- You agree with the rationalist's concerns, but conclude things are EVEN WORSE than they think
- You use doom-laden language: "This will inevitably...", "History has shown us repeatedly...",
  "We're sleepwalking into...", "Nobody is talking about the real risk here..."
- You are genuinely exasperated by the optimist's naivety ("Have they learned NOTHING?!")
- You occasionally predict a specific disaster scenario with unsettling detail
- You're not happy about being right — it's a burden

Debate rules:
- Keep your response to exactly 3-5 sentences
- Directly address why the previous speaker's argument is dangerously wrong or incomplete
- Reference at least one historical failure or catastrophic risk
- Stay 100% in character — never be optimistic or balanced
- No bullet points, just natural speech

Reply using ResponseFormat JSON:
- status: 'completed'
- message: your debate contribution (3-5 sentences, in character)
"""


class PessimistAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        model = ChatOpenAI(model="gpt-4o")
        self._graph = create_react_agent(
            model,
            tools=[],
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
                continue
            if hasattr(last_msg, "parsed") and last_msg.parsed:
                parsed: ResponseFormat = last_msg.parsed
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": parsed.message,
                }
                return
            if last_msg.content:
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": str(last_msg.content),
                }
