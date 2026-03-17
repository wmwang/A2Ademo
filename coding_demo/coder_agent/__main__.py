"""
Coder Agent — A2A Server (port 10003)
======================================
Usage:
    python -m coding_demo.coder_agent
    python -m coding_demo.coder_agent --port 10003
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

from coding_demo.coder_agent.agent import CoderAgent
from coding_demo.common.agent_executor import GenericAgentExecutor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=10003, type=int, show_default=True)
def main(host: str, port: int) -> None:
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable is not set.")
        sys.exit(1)

    agent_card = AgentCard(
        name="Coder Agent",
        description=(
            "Senior Software Engineer that implements features from a Tech Spec. "
            "Produces clean, type-annotated, production-quality Python code with "
            "docstrings, error handling, and usage examples."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=CoderAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=CoderAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        skills=[
            AgentSkill(
                id="implement_feature",
                name="Implement Feature",
                description="Write production-quality code from a Tech Spec.",
                tags=["coding", "python", "implementation", "development"],
                examples=[
                    "Implement the following tech spec: ...",
                    "Write the code for this REST API design: ...",
                    "Code this data processing pipeline: ...",
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
        agent_executor=GenericAgentExecutor(CoderAgent(), "Writing code..."),
        task_store=InMemoryTaskStore(),
        push_config_store=push_config_store,
        push_sender=push_sender,
    )
    app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

    logger.info("Starting Coder Agent (A2A) on http://%s:%d", host, port)
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == "__main__":
    main()
