"""
Generic A2A AgentExecutor
=========================
Reusable adapter that bridges any agent with a .stream(query, session_id)
interface to the a2a-sdk request lifecycle.
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

logger = logging.getLogger(__name__)


class GenericAgentExecutor(AgentExecutor):
    """Connects the A2A request lifecycle to any agent with a .stream() method."""

    def __init__(self, agent, working_message: str = "Thinking..."):
        self.agent = agent
        self.working_message = working_message

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        if not query:
            raise ServerError(error=InvalidParamsError())

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
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item["content"], task.context_id, task.id
                        ),
                    )
                elif needs_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item["content"], task.context_id, task.id
                        ),
                        final=True,
                    )
                    break
                else:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item["content"]))],
                        name="result",
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.error("Error streaming agent response: %s", e)
            raise ServerError(error=InternalError()) from e

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())
