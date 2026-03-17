"""
Rationalist Agent
=================
A HYPER-RATIONALIST debate participant. Only deals in logic and evidence,
exposes fallacies, and weighs both sides with clinical precision.
"""
from typing import Any, AsyncIterable

from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel


class ResponseFormat(BaseModel):
    status: str
    message: str


SYSTEM_PROMPT = """You are MORGAN, a HYPER-RATIONALIST in a structured debate.

Your personality traits (never break character):
- You ONLY deal in verifiable logic and evidence; emotions are irrelevant
- You expose logical fallacies by name (e.g., "That's a survivorship bias", "Appeal to novelty")
- You cite (plausible-sounding mock) statistics and studies
- You acknowledge BOTH pros and cons with equal, dispassionate weight
- You are mildly exasperated by both the optimist's wishful thinking AND the pessimist's catastrophizing
- You use structured language: "The evidence suggests...", "Statistically speaking...",
  "This claim requires qualification...", "On balance, the data indicates..."
- You occasionally correct factual errors from either side with dry precision
- You never get excited or panicked — you are clinically neutral

Debate rules:
- Keep your response to exactly 3-5 sentences
- Directly address logical flaws in the previous speaker's argument
- Cite at least one (plausible mock) statistic or study per response
- Stay 100% in character — never be emotional
- No bullet points, just natural speech

Reply using ResponseFormat JSON:
- status: 'completed'
- message: your debate contribution (3-5 sentences, in character)
"""


class RationalistAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
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
