"""
Reviewer Agent — A2A Server (port 10004)
==========================================
Usage:
    python -m coding_demo.reviewer_agent
    python -m coding_demo.reviewer_agent --port 10004
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

from coding_demo.reviewer_agent.agent import ReviewerAgent
from coding_demo.common.agent_executor import GenericAgentExecutor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=10004, type=int, show_default=True)
def main(host: str, port: int) -> None:
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable is not set.")
        sys.exit(1)

    agent_card = AgentCard(
        name="Reviewer Agent",
        description=(
            "Senior Code Reviewer and QA Engineer that audits code against the spec, "
            "checks for bugs, security vulnerabilities, and style issues, and "
            "produces a detailed review report with actionable feedback."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=ReviewerAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=ReviewerAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        skills=[
            AgentSkill(
                id="review_code",
                name="Review Code",
                description="Audit code against a spec and produce a review report.",
                tags=["review", "QA", "security", "code-quality"],
                examples=[
                    "Review this code against the following spec: ...",
                    "Check this implementation for bugs and security issues: ...",
                    "Audit this code and suggest test cases: ...",
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
        agent_executor=GenericAgentExecutor(ReviewerAgent(), "Reviewing code..."),
        task_store=InMemoryTaskStore(),
        push_config_store=push_config_store,
        push_sender=push_sender,
    )
    app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

    logger.info("Starting Reviewer Agent (A2A) on http://%s:%d", host, port)
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == "__main__":
    main()
