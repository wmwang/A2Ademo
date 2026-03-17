"""
Architect Agent — A2A Server (port 10002)
==========================================
Usage:
    python -m coding_demo.architect_agent
    python -m coding_demo.architect_agent --port 10002
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

from coding_demo.architect_agent.agent import ArchitectAgent
from coding_demo.common.agent_executor import GenericAgentExecutor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=10002, type=int, show_default=True)
def main(host: str, port: int) -> None:
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable is not set.")
        sys.exit(1)

    agent_card = AgentCard(
        name="Architect Agent",
        description=(
            "Senior Software Architect that designs system structure, defines "
            "component interfaces, picks design patterns, and produces a detailed "
            "Tech Spec for the Coder to implement."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=ArchitectAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=ArchitectAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        skills=[
            AgentSkill(
                id="design_tech_spec",
                name="Design Tech Spec",
                description="Produce a structured Tech Spec from feature requirements.",
                tags=["architecture", "design", "tech-spec", "patterns"],
                examples=[
                    "Design a REST API for user authentication with JWT",
                    "Architect a simple task queue with retry logic",
                    "Create a spec for a CSV-to-JSON data transformer",
                ],
            )
        ],
    )

    httpx_client = httpx.AsyncClient()
    push_config_store = InMemoryPushNotificationConfigStore()
    push_sender = BasePushNotificationSender(
        httpx_client=httpx_client,
        config_store=push_config_store,
    )
    request_handler = DefaultRequestHandler(
        agent_executor=GenericAgentExecutor(ArchitectAgent(), "Designing architecture..."),
        task_store=InMemoryTaskStore(),
        push_config_store=push_config_store,
        push_sender=push_sender,
    )
    app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

    logger.info("Starting Architect Agent (A2A) on http://%s:%d", host, port)
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == "__main__":
    main()
