from collections.abc import AsyncGenerator
from typing import Any

from langchain.agents import AgentState
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langchain_core.messages.ai import add_ai_message_chunks
from langchain_core.runnables import RunnableConfig
from langfuse.langchain import CallbackHandler
from langgraph.types import Command, Interrupt, StateSnapshot, StreamPart
from uuid_utils.compat import UUID

from agents.supervisor import Supervisor
from core.config import settings
from core.context import Context
from core.definitions import LANGCHAIN_API_VERSION
from core.errors import (
    InvalidCommandDecisionError,
    MissingInterruptCommandError,
    RequiredEditedArgsError,
)
from core.pii.stream_transformers.base_stream_transformer import (
    BasePIIStreamTransformer,
)
from dtos.agent import (
    AgentConfig,
    AgentInterruptCommand,
    AgentRequest,
    AgentResponse,
    AgentStateResponse,
    AgentToolInterrupt,
)
from dtos.common import SSEEvent
from persistence.parsers.message_parsers import LCMessage
from persistence.repos.base_conversation_repository import BaseConversationRepository

langfuse_handler = CallbackHandler()


class AgentService:
    """Service class for handling agent requests and responses."""

    def __init__(
        self,
        supervisor: Supervisor,
        *,
        stream_transformer: BasePIIStreamTransformer,
        conversation_repo: BaseConversationRepository,
    ) -> None:
        """Initialize the AgentService.

        Args:
            supervisor: The supervisor to use for the agent.
            stream_transformer: The stream transformer to use.
            conversation_repo: The conversation repository to use.
        """
        self.__graph = supervisor
        self._stream_transformer = stream_transformer
        self._conversation_repo = conversation_repo  # TODO: Use it

        self.default_interrupt_msg = AIMessage(
            content=(
                'Hay acciones pendientes de revisión. Por favor, revisa las acciones'
                ' y aprueba, edita o rechaza cada una según corresponda.'
            )
        )

    async def invoke(
        self,
        request: AgentRequest,
        context: Context | None = None,
    ) -> AgentResponse:
        """Invoke the agent with the given request and context.

        Args:
            request: The request to invoke the agent with.
            context: The context to invoke the agent with. Defaults to None.

        Returns:
            The response from the agent.
        """
        user_id = context.user_id if context else None

        input_, response = await self._parse_request(request, user_id)
        if response:
            return response

        response = await self.__graph.ainvoke(
            input_,
            config=self._get_runnable_config(request),
            context=context,
            version=LANGCHAIN_API_VERSION,
        )

        ai_msg = response.value['messages'][-1]

        interrupts = []
        if response.interrupts:
            ai_msg = ai_msg if ai_msg.content else self.default_interrupt_msg
            interrupts = self._parse_interrupts_to_response_objects(response.interrupts)

        if user_id:
            await self._create_or_update_conversation(
                user_id=user_id,
                thread_id=request.thread_id,
                messages=response.value['messages'],
                interrupts=interrupts,
            )

        return AgentResponse(
            message=ai_msg if ai_msg.content else self.default_interrupt_msg,
            interrupts=interrupts,
            thread_id=request.thread_id,
        )

    async def stream(
        self,
        request: AgentRequest,
        context: Context | None = None,
    ) -> AsyncGenerator[SSEEvent[AgentResponse]]:
        """Stream the response from the agent with the given request and context.

        Args:
            request: The request to stream the agent with.
            context: The context to stream the agent with. Defaults to None.

        Yields:
            The SSE events from the agent, which can be either a chunk of the response
            or the final response.
        """
        user_id = context.user_id if context else None

        input_, response = await self._parse_request(request, user_id)
        if response:
            yield SSEEvent(event='end', data=response)
            return

        thread_id = request.thread_id
        ai_msg_chunks_buffer: list[AIMessageChunk] = []

        try:
            async for chunk in self.__graph.astream(
                input_,
                config=self._get_runnable_config(request),
                context=context,
                stream_mode=['messages'],
                version=LANGCHAIN_API_VERSION,
            ):
                if event := self._parse_stream_part(
                    chunk, ai_msg_chunks_buffer, thread_id
                ):
                    yield event

            if flush := self._stream_transformer.flush_buffer(str(thread_id)):
                yield SSEEvent(
                    event='chunk',
                    data=AgentResponse(
                        message=flush,
                        thread_id=thread_id,
                    ),
                )

            state = await self.get_state(request.thread_id)
            ai_msg = state.values['messages'][-1]

            interrupts = []
            if state.interrupts:
                ai_msg = ai_msg if ai_msg.content else self.default_interrupt_msg
                interrupts = self._parse_interrupts_to_response_objects(
                    state.interrupts
                )

            if user_id:
                await self._create_or_update_conversation(
                    user_id=user_id,
                    thread_id=request.thread_id,
                    messages=state.values['messages'],
                    interrupts=interrupts,
                )

            yield SSEEvent(
                event='end',
                data=AgentResponse(
                    message=ai_msg,
                    interrupts=interrupts,
                    thread_id=thread_id,
                ),
            )

        finally:
            if request.thread_id:
                self._stream_transformer.drop_buffer(str(request.thread_id))

    async def get_state(self, thread_id: UUID) -> StateSnapshot:
        """Return the current state of the thread."""
        return await self.__graph.aget_state(
            config=RunnableConfig(
                configurable={
                    'thread_id': thread_id,
                },
            )
        )

    async def clean_state(self, thread_id: UUID) -> None:
        """Clean the state of the thread."""
        await self.__graph.checkpointer.adelete_thread(thread_id=str(thread_id))  # type: ignore

    def parse_state_to_response(self, state: StateSnapshot) -> AgentStateResponse:
        """Parse the state snapshot into a response object.

        Response contains messages and interrupts.
        """
        messages = state.values.get('messages', [])
        interrupts = self._parse_interrupts_to_response_objects(state.interrupts)
        return AgentStateResponse(messages=messages, interrupts=interrupts)

    async def _parse_request(
        self, request: AgentRequest, user_id: str | None = None
    ) -> tuple[AgentState | Command | None, AgentResponse | None]:
        """Parse the request.

        Returns either an AgentState or a Command, depending on whether there are
        interrupts in the state. If there are interrupts, it checks if the request
        has commands for the interrupts. Otherwise, it returns an AgentResponse with
        the default interrupt message and the interrupts.

        Args:
            request: The request to parse.
            user_id: The ID of the user making the request. This is used to resume
                interrupts and update the conversation. If not provided, interrupts
                will not be resumed and the conversation will not be updated.

        Raises:
            MissingInterruptCommandError: If there are interrupts in the state and
                the request does not have commands for all of them.

        Returns:
            A tuple of either an AgentState or a Command, and an AgentResponse or None.
        """
        state = await self.get_state(request.thread_id)

        if state.interrupts:
            interrupts = self._parse_interrupts_to_response_objects(state.interrupts)
            if not request.input.commands:
                return None, AgentResponse(
                    message=self.default_interrupt_msg,
                    interrupts=interrupts,
                    thread_id=request.thread_id,
                )

            input_, missing = await self._get_resume_command_for_interrupts(
                interrupts=interrupts,
                commands=request.input.commands,
                user_id=user_id,
            )
            if missing:
                raise MissingInterruptCommandError(missing)

        else:
            query = request.input.query
            input_ = AgentState(messages=[HumanMessage(content=query)])

        return input_, None

    def _parse_stream_part(
        self,
        chunk: StreamPart[Any, Any],
        ai_msg_chunks_buffer: list[AIMessageChunk],
        thread_id: UUID,
    ) -> SSEEvent[AgentResponse] | None:
        """Parse a stream part from the agent into an SSEEvent object.

        Args:
            chunk: The stream part from the agent.
            ai_msg_chunks_buffer: A buffer to hold AIMessageChunks until a complete
                message is formed.
            thread_id: The thread ID for the agent.

        Returns:
            An SSEEvent object containing the chunk of the response, or None if the
            chunk is not relevant.
        """
        if chunk['type'] != 'messages':
            return None

        msg, metadata = chunk['data']
        if metadata.get('langgraph_node') not in ('model', 'tools'):
            return None

        if isinstance(msg, AIMessageChunk) and not msg.content and msg.tool_call_chunks:
            ai_msg_chunks_buffer.append(msg)
            return None

        if ai_msg_chunks_buffer:
            ai_msg = add_ai_message_chunks(*ai_msg_chunks_buffer)
            ai_msg_chunks_buffer.clear()
            return SSEEvent(
                event='chunk',
                data=AgentResponse(
                    message=ai_msg,
                    thread_id=thread_id,
                ),
            )

        if msg := self._stream_transformer.transform_stream_chunk(msg, str(thread_id)):
            return SSEEvent(
                event='chunk',
                data=AgentResponse(
                    message=msg,
                    thread_id=thread_id,
                ),
            )

        return None

    async def _create_or_update_conversation(
        self,
        user_id: str,
        thread_id: UUID,
        messages: list[BaseMessage],
        interrupts: list[AgentToolInterrupt],
    ) -> None:
        """Creates or updates a conversation based on the request and response.

        If the conversation does not exist, it creates a new one. If it exists,
        it updates the conversation with the new message and any interrupts.
        """
        messages_to_add = self._get_msgs_till_human_msg(messages)
        if not messages_to_add:
            return

        first_msg = messages_to_add[0]
        last_msg = messages_to_add.pop(-1)

        conversation = await self._conversation_repo.get_conversation_by_thread_id(
            thread_id
        )
        if not conversation:
            conversation = await self._conversation_repo.create_conversation(
                user_id=user_id,
                thread_id=thread_id,
                title=str(first_msg.content)[:60],
            )

        for msg in messages_to_add:
            if not isinstance(msg, LCMessage):
                continue
            await self._conversation_repo.add_message_to_conversation(
                conversation_id=conversation.id,
                lc_message=msg,
            )

        if first_msg != last_msg and isinstance(last_msg, LCMessage):
            await self._conversation_repo.add_message_to_conversation(
                conversation_id=conversation.id,
                lc_message=last_msg,
                interrupts=interrupts,
            )

    def _get_msgs_till_human_msg(
        self, messages: list[BaseMessage]
    ) -> list[BaseMessage]:
        """Returns the messages until the last human message.

        If there is no human message, returns all messages.
        """
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], HumanMessage):
                return messages[: i + 1]
        return messages

    def _get_runnable_config(self, config_request: AgentConfig) -> RunnableConfig:
        """Get the RunnableConfig for the agent based on the request and settings."""
        max_concurrency = (
            min(config_request.max_concurrency, settings.max_concurrency)
            if config_request.max_concurrency
            else settings.max_concurrency
        )

        recursion_limit = (
            min(config_request.recursion_limit, settings.max_recursion_limit)
            if config_request.recursion_limit
            else settings.max_recursion_limit
        )

        callbacks = []
        if settings.use_langfuse:
            callbacks.append(langfuse_handler)

        return RunnableConfig(
            configurable={
                'thread_id': config_request.thread_id,
            },
            tags=config_request.tags,
            metadata=config_request.metadata,
            callbacks=callbacks,
            max_concurrency=max_concurrency,
            recursion_limit=recursion_limit,
        )

    def _parse_interrupts_to_response_objects(
        self, interrupts: tuple[Interrupt, ...]
    ) -> list[AgentToolInterrupt]:
        """Parse the interrupts into a list of AgentToolInterrupt objects."""
        response_interrupts = []
        for interrupt in interrupts:
            merged_request_and_review = zip(
                interrupt.value['action_requests'],
                interrupt.value['review_configs'],
                strict=True,
            )
            for action_request, review_config in merged_request_and_review:
                response_interrupts.append(
                    AgentToolInterrupt(
                        id=interrupt.id,
                        name=action_request['name'],
                        args=action_request['args'],
                        description=action_request['description'].split('\n', 1)[0],
                        allowed_decisions=review_config['allowed_decisions'],
                    )
                )
        return response_interrupts

    async def _get_resume_command_for_interrupts(
        self,
        interrupts: list[AgentToolInterrupt],
        commands: dict[str, AgentInterruptCommand],
        user_id: str | None = None,
    ) -> tuple[Command, list[str]]:
        """Get the resume command for the interrupts based on the commands provided.

        Args:
            interrupts: The list of interrupts that need to be resumed.
            commands: A dictionary of commands provided by the user,
                keyed by interrupt ID.
            user_id: The ID of the user who is resuming the interrupts.

        Raises:
            InvalidCommandDecisionError: If a command decision is invalid.
            RequiredEditedArgsError: If an edited action is required for an interrupt
                but not provided.

        Returns:
            A tuple containing the Command to resume the interrupts and a list of
            missing interrupt IDs that do not have corresponding commands.
        """
        decisions = []
        missing = []

        for interrupt in interrupts:
            command = commands.get(interrupt.id)
            if not command:
                missing.append(f'{interrupt.name} ({interrupt.id})')
                continue

            if command.decision == 'approve':
                decision = {'type': 'approve'}

            elif command.decision == 'edit':
                if not command.edited_args:
                    raise RequiredEditedArgsError(interrupt.name)

                decision = {
                    'type': 'edit',
                    'edited_action': {
                        'name': command.name,
                        'args': command.edited_args,
                    },
                }

            elif command.decision == 'reject':
                decision = {
                    'type': 'reject',
                    'message': command.reject_reason
                    or 'User rejected this action. Do not retry this tool call.',
                }

            else:
                raise InvalidCommandDecisionError(command.decision, interrupt.name)

            decisions.append(decision)

            await self._conversation_repo.resume_interrupt(
                execution_id=interrupt.id,
                command=command,
                reviewer_id=user_id,
            )

        return Command(resume={'decisions': decisions}), missing
