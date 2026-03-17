"""Rationalist Agent — A2A Server (port 10006)"""
import logging, os, sys
import click, httpx, uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import BasePushNotificationSender, InMemoryPushNotificationConfigStore, InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv
from debate_demo.rationalist_agent.agent import RationalistAgent
from coding_demo.common.agent_executor import GenericAgentExecutor

load_dotenv()
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10006, type=int)
def main(host: str, port: int) -> None:
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY not set"); sys.exit(1)

    agent_card = AgentCard(
        name="Morgan the Rationalist",
        description="A hyper-rationalist debate participant who only deals in logic and evidence.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=RationalistAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=RationalistAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        skills=[AgentSkill(id="debate", name="Debate", description="Participate in structured debate as a hyper-rationalist.", tags=["debate", "rationalist"])],
    )
    httpx_client = httpx.AsyncClient()
    push_cfg = InMemoryPushNotificationConfigStore()
    request_handler = DefaultRequestHandler(
        agent_executor=GenericAgentExecutor(RationalistAgent(), "Analysing logically..."),
        task_store=InMemoryTaskStore(),
        push_config_store=push_cfg,
        push_sender=BasePushNotificationSender(httpx_client=httpx_client, config_store=push_cfg),
    )
    app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)
    logger.warning("Starting Rationalist Agent on http://%s:%d", host, port)
    uvicorn.run(app.build(), host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
