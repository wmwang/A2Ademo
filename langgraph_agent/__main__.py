"""
LangGraph Lot Status Agent — A2A Server
========================================
Starts an HTTP server that speaks the A2A protocol, wrapping the LangGraph
LotStatusAgent.  Any A2A-compatible client (e.g. Google ADK) can connect to it.

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

from langgraph_agent.agent import LotStatusAgent
from langgraph_agent.agent_executor import LotStatusAgentExecutor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=10001, type=int, show_default=True)
def main(host: str, port: int) -> None:
    """Start the LangGraph Lot Status Agent as an A2A server."""

    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable is not set.")
        sys.exit(1)

    # ── Agent Card: describes this agent to any A2A client ──────────────────
    agent_card = AgentCard(
        name="LangGraph Fab WIP Agent",
        description=(
            "A semiconductor fab WIP (Work-In-Process) expert powered by "
            "LangGraph + Gemini. Queries lot status, process history, and "
            "hold information from the fab WIP system."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=LotStatusAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=LotStatusAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        skills=[
            AgentSkill(
                id="lot_status_query",
                name="Lot Status Query",
                description=(
                    "Query semiconductor lot WIP status, process history, "
                    "and hold information by lot ID."
                ),
                tags=["semiconductor", "fab", "WIP", "lot", "manufacturing", "process"],
                examples=[
                    "What is the status of lot LOT-2024-001?",
                    "Show me the process history for lot A12345",
                    "Which lots are currently on hold?",
                    "Is lot B20045 still in Photolithography?",
                    "What equipment is lot LOT-2024-017 on right now?",
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
        agent_executor=LotStatusAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_config_store=push_config_store,
        push_sender=push_sender,
    )
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    logger.info("Starting LangGraph Fab WIP Agent (A2A) on http://%s:%d", host, port)
    logger.info("Agent card: http://%s:%d/.well-known/agent.json", host, port)
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == "__main__":
    main()
