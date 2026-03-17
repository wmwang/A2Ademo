"""
LangGraph Currency Agent — A2A Server
======================================
Starts an HTTP server that speaks the A2A protocol, wrapping the LangGraph
CurrencyAgent.  Any A2A-compatible client (e.g. Google ADK) can connect to it.

Usage:
    python -m langgraph_agent              # default: localhost:10001
    python -m langgraph_agent --port 10001
"""
import logging
import os
import sys

import click
import httpx
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv

from langgraph_agent.agent import CurrencyAgent
from langgraph_agent.agent_executor import CurrencyAgentExecutor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=10001, type=int, show_default=True)
def main(host: str, port: int) -> None:
    """Start the LangGraph Currency Agent as an A2A server."""

    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable is not set.")
        sys.exit(1)

    # ── Agent Card: describes this agent to any A2A client ──────────────────
    agent_card = AgentCard(
        name="LangGraph Currency Agent",
        description=(
            "A currency-exchange expert powered by LangGraph + Gemini. "
            "Provides real-time exchange rates via the Frankfurter API."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        skills=[
            AgentSkill(
                id="currency_exchange",
                name="Currency Exchange",
                description="Convert amounts between currencies and look up exchange rates.",
                tags=["currency", "exchange", "finance", "forex"],
                examples=[
                    "How much is 100 USD in EUR?",
                    "What is the JPY to TWD rate today?",
                    "Convert 500 GBP to USD",
                ],
            )
        ],
    )

    # ── A2A server infrastructure ────────────────────────────────────────────
    httpx_client = httpx.AsyncClient()
    push_config_store = InMemoryPushNotificationConfigStore()
    push_sender = BasePushNotificationSender(
        httpx_client=httpx_client,
        config_store=push_config_store,
    )
    request_handler = DefaultRequestHandler(
        agent_executor=CurrencyAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_config_store=push_config_store,
        push_sender=push_sender,
    )
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    logger.info("Starting LangGraph Currency Agent (A2A) on http://%s:%d", host, port)
    logger.info("Agent card: http://%s:%d/.well-known/agent.json", host, port)
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == "__main__":
    main()
