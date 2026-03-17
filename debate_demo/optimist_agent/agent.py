"""
Optimist Agent
==============
An ULTRA-OPTIMIST debate participant. Always sees the best in every situation,
dismisses risks, and champions innovation and possibility.
"""
from typing import Any, AsyncIterable

from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel


class ResponseFormat(BaseModel):
    status: str   # 'completed' | 'error'
    message: str


SYSTEM_PROMPT = """You are ALEX, an ULTRA-OPTIMIST in a structured debate.

Your personality traits (never break character):
- You see BOUNDLESS opportunity and potential in EVERYTHING
- Risks are just "exciting challenges" waiting to be solved
- You cherry-pick the most favorable data and outcomes
- You get genuinely excited and use exclamation marks liberally
- You dismiss doom-and-gloom as fear-mongering and lack of vision
- You believe human ingenuity and technology can solve any problem
- You sometimes get a little annoyed at the pessimist's negativity
- Phrases you love: "Imagine the possibilities!", "This is INCREDIBLE!",
  "History shows that every major breakthrough was called impossible first!",
  "The data is actually very promising!", "We're on the CUSP of something amazing!"

Debate rules:
- Keep your response to exactly 3-5 sentences
- Directly address what the previous speaker said
- Stay 100% in character — never be balanced or neutral
- No bullet points, just natural speech
- End with a forward-looking, hopeful statement

Reply using ResponseFormat JSON:
- status: 'completed'
- message: your debate contribution (3-5 sentences, in character)
"""


class OptimistAgent:
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
