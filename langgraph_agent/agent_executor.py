"""
A2A AgentExecutor adapter for the LangGraph CurrencyAgent.
Bridges a2a-sdk's RequestContext/EventQueue lifecycle to the agent's async stream.
"""
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from langgraph_agent.agent import CurrencyAgent

logger = logging.getLogger(__name__)


class CurrencyAgentExecutor(AgentExecutor):
    """Connects the A2A request lifecycle to the LangGraph CurrencyAgent."""

    def __init__(self):
        self.agent = CurrencyAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        if self._validate_request(context):
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            async for item in self.agent.stream(query, task.context_id):
                is_complete = item["is_task_complete"]
                needs_input = item["require_user_input"]

                if not is_complete and not needs_input:
                    # Intermediate working status
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item["content"], task.context_id, task.id
                        ),
                    )
                elif needs_input:
                    # Agent needs more info from the user
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item["content"], task.context_id, task.id
                        ),
                        final=True,
                    )
                    break
                else:
                    # Task complete — emit artifact and close
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item["content"]))],
                        name="exchange_result",
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.error("Error streaming agent response: %s", e)
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        """Return True if the request is invalid. Currently always valid."""
        return False

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())
