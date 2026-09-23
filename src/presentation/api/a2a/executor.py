from typing import Any

from a2a.helpers import (
    new_data_part,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState
from langchain_core.messages import AIMessage

from agents.context import Context
from dtos.agent import AgentInput, AgentRequest
from services.agent_service import AgentService
from utils.uuid import str_uuid7


class A2AAgentExecutor(AgentExecutor):
    """An implementation of the AgentExecutor interface.

    Attributes:
        _agent_service: An instance of AgentService used to handle agent requests.
    """

    def __init__(self, agent_service: AgentService | None = None) -> None:
        """Initialize the A2AAgentExecutor.

        Args:
            agent_service: An instance of AgentService used to handle agent requests.
                Defaults to None.
        """
        self._agent_service = agent_service

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task = await self._get_current_task_or_create_new(context, event_queue)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message('Processing request...'),
        )

        query = context.get_user_input()
        metadata = context.metadata

        if query:
            request = AgentRequest(
                thread_id=context.context_id or str_uuid7(),
                input=AgentInput(query=query),
            )
            await self._handle_stream(updater, request, metadata)
        else:
            result = 'No input provided.'
            await updater.add_artifact(
                parts=[
                    new_text_part(
                        text=result,
                        media_type='text/plain',
                    )
                ]
            )

        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message('Request is completed.'),
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task = context.current_task
        if task is None:
            return

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )

        await updater.update_status(
            state=TaskState.TASK_STATE_CANCELED,
            message=new_text_message('Request has been canceled.'),
        )

    async def _get_current_task_or_create_new(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> Task:
        task = context.current_task

        if task is None:
            if context.message is None:
                raise ValueError('No message found in context for new task creation.')
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        return task

    async def _handle_stream(
        self, updater: TaskUpdater, request: AgentRequest, metadata: dict[str, Any]
    ) -> None:
        service = self._agent_service or AgentService.get_instance()
        context = self._build_context_from_metadata(metadata)

        async for event in service.stream(request, context):
            if event.event == 'end':
                interrupts = event.data.interrupts
                await updater.add_artifact(
                    parts=[
                        new_text_part(
                            text='Interrupts detected during processing.',
                            media_type='text/plain',
                        ),
                        new_data_part(
                            data={
                                'interrupts': [
                                    interrupt.model_dump() for interrupt in interrupts
                                ]
                            },
                            media_type='application/json',
                        ),
                    ]
                )
                break

            message = event.data.message
            if isinstance(message, AIMessage) and message.content:
                await updater.add_artifact(
                    parts=[
                        new_text_part(
                            text=str(event.data.message.content),
                            media_type='text/plain',
                        )
                    ]
                )

    def _build_context_from_metadata(self, metadata: dict[str, Any]) -> Context:
        return Context(
            user_id=metadata.get('user_id', ''),
        )
