from __future__ import annotations

import logging
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

from coding_demo.common.agent_executor import GenericAgentExecutor
from debate_demo.model_config import load_model_settings
from scrum_meeting_demo.role_agent import RoleAgent
from scrum_meeting_demo.roles import MeetingRole

load_dotenv()
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def build_main(role: MeetingRole):
    @click.command()
    @click.option("--host", default="localhost", show_default=True)
    @click.option("--port", default=role.port, type=int, show_default=True)
    def main(host: str, port: int) -> None:
        try:
            load_model_settings()
        except RuntimeError as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)

        agent_card = AgentCard(
            name=f"{role.name} the {role.title}",
            description=role.card_description,
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=RoleAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=RoleAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=AgentCapabilities(streaming=True, push_notifications=True),
            skills=[
                AgentSkill(
                    id=role.skill_id,
                    name=role.skill_name,
                    description=role.card_description,
                    tags=list(role.tags),
                    examples=list(role.examples),
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
            agent_executor=GenericAgentExecutor(
                RoleAgent(role.system_prompt),
                f"{role.title} is reviewing the discussion...",
            ),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config_store,
            push_sender=push_sender,
        )
        app = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )

        logger.warning("Starting %s on http://%s:%d", role.title, host, port)
        uvicorn.run(app.build(), host=host, port=port, log_level="warning")

    return main
