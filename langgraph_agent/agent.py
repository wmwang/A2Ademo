"""
LangGraph Currency Agent
========================
A currency exchange expert built with LangGraph + Gemini.
Exposed as an A2A server so any A2A-compatible client (e.g., Google ADK) can call it.
"""
import os
from typing import Any, AsyncIterable

import httpx
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel


# ── Tool ──────────────────────────────────────────────────────────────────────

@tool
def get_exchange_rate(
    currency_from: str = "USD",
    currency_to: str = "EUR",
    currency_date: str = "latest",
) -> dict:
    """Fetch the current exchange rate between two currencies.

    Args:
        currency_from: Source currency code (e.g. USD, EUR, JPY).
        currency_to: Target currency code (e.g. EUR, JPY, TWD).
        currency_date: Date for the rate in YYYY-MM-DD format, or 'latest'.

    Returns:
        A dict with the exchange rate data from the Frankfurter API.
    """
    try:
        response = httpx.get(
            f"https://api.frankfurter.app/{currency_date}",
            params={"from": currency_from, "to": currency_to},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        return {"error": f"HTTP error fetching exchange rate: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


# ── Structured response format ────────────────────────────────────────────────

class ResponseFormat(BaseModel):
    """Structured response from the currency agent."""
    status: str   # 'input_required' | 'completed' | 'error'
    message: str  # Human-readable answer or clarification request


# ── Agent ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a currency exchange expert assistant.
Help users convert between currencies and look up exchange rates.

Use the get_exchange_rate tool to fetch real-time rates.

Always reply in the ResponseFormat JSON schema:
- status: 'completed'      → you have answered the question
- status: 'input_required' → you need more information from the user
- status: 'error'          → an error occurred

Keep your message concise and include the numeric rate/amount.
Only answer currency-related questions. Politely decline anything else."""


class CurrencyAgent:
    """LangGraph ReAct agent for currency exchange queries."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
        self._graph = create_react_agent(
            model,
            tools=[get_exchange_rate],
            checkpointer=MemorySaver(),
            prompt=SYSTEM_PROMPT,
            response_format=ResponseFormat,
        )

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """Stream agent responses for a given query.

        Yields dicts with keys:
            is_task_complete (bool)
            require_user_input (bool)
            content (str)
        """
        config = {"configurable": {"thread_id": session_id}}

        async for chunk in self._graph.astream(
            {"messages": [("human", query)]},
            config,
            stream_mode="values",
        ):
            last_msg = chunk["messages"][-1]

            if not isinstance(last_msg, AIMessage):
                continue

            # Tool call in progress → emit working status
            if last_msg.tool_calls:
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Looking up exchange rates...",
                }
                continue

            # Structured response via response_format
            if hasattr(last_msg, "parsed") and last_msg.parsed:
                parsed: ResponseFormat = last_msg.parsed
                yield {
                    "is_task_complete": parsed.status == "completed",
                    "require_user_input": parsed.status == "input_required",
                    "content": parsed.message,
                }
                return

            # Fallback: plain text content
            if last_msg.content:
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": str(last_msg.content),
                }
