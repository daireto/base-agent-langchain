from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from langchain.agents import AgentState
from langchain_core.messages import AIMessage, AIMessageChunk, AnyMessage, HumanMessage
from langchain_core.messages.ai import add_ai_message_chunks
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, Interrupt, StateSnapshot, StreamPart
from uuid_utils.compat import UUID

from agents.context import Context
from agents.supervisor.agent import Supervisor
from core.config import settings
from core.definitions import DEFAULT_USER_ID, LANGCHAIN_API_VERSION
from core.errors import (
    InvalidCommandDecisionError,
    MissingInterruptCommandError,
    RequiredEditedArgsError,
)
from core.langfuse_resources import langfuse_handler
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
from utils.messages import get_messages_from_user_msg
from utils.singleton import SingletonMeta


@dataclass
class _ParsedAgentRequest:
    """Represents a parsed request to an agent."""

    input: AgentState | Command | None
    response: AgentResponse | None
    interrupts: list[AgentToolInterrupt]


class AgentService(metaclass=SingletonMeta):
    """Service class for handling agent requests and responses.

    Attributes:
        _graph: The compiled graph that manages the agent's state and execution.
        _stream_transformer: The stream transformer for handling streaming responses.
        _conversation_repo: The repository for managing conversations.
    """

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
        self._graph = supervisor
        self._stream_transformer = stream_transformer
        self._conversation_repo = conversation_repo

        self._default_interrupt_msg = (
            'Hay acciones pendientes de revisión. Por favor, revisa las acciones'
            ' y aprueba, edita o rechaza cada una según corresponda.'
        )
        self._default_resume_msg = 'Acciones revisadas'

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

        parsed_request = await self._parse_request(request)
        if parsed_request.response:
            return parsed_request.response

        response = await self._graph.ainvoke(
            parsed_request.input,
            config=self._get_runnable_config(request, context),
            context=context,
            version=LANGCHAIN_API_VERSION,
        )

        if request.input.commands:
            await self._resume_interrupts(
                parsed_request.interrupts, request.input.commands, user_id
            )

        ai_msg: AIMessage = response.value['messages'][-1]

        interrupts = []
        if response.interrupts:
            ai_msg.additional_kwargs['__interrupted__'] = True
            if not ai_msg.content:
                ai_msg.content = self._default_interrupt_msg
            interrupts = self._parse_interrupts_to_response_objects(response.interrupts)

        if user_id:
            await self._create_or_update_conversation(
                user_id=user_id,
                thread_id=request.thread_id,
                messages=response.value['messages'],
                interrupts=interrupts,
            )

        return AgentResponse(
            message=ai_msg,
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

        parsed_request = await self._parse_request(request)
        if parsed_request.response:
            yield SSEEvent(event='end', data=parsed_request.response)
            return

        thread_id = request.thread_id
        ai_msg_chunks_buffer: list[AIMessageChunk] = []

        try:
            async for chunk in self._graph.astream(
                parsed_request.input,
                config=self._get_runnable_config(request, context),
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

            if request.input.commands:
                await self._resume_interrupts(
                    parsed_request.interrupts, request.input.commands, user_id
                )

            state = await self.get_state(request.thread_id)
            ai_msg: AIMessage = state.values['messages'][-1]

            interrupts = []
            if state.interrupts:
                ai_msg.additional_kwargs['__interrupted__'] = True
                if not ai_msg.content:
                    ai_msg.content = self._default_interrupt_msg
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
        return await self._graph.aget_state(
            config=RunnableConfig(
                configurable={
                    'thread_id': str(thread_id),
                },
            )
        )

    async def clean_state(self, thread_id: UUID) -> None:
        """Clean the state of the thread."""
        await self._graph.checkpointer.adelete_thread(thread_id=str(thread_id))  # type: ignore

    def parse_state_to_response(self, state: StateSnapshot) -> AgentStateResponse:
        """Parse the state snapshot into a response object.

        Response contains messages and interrupts.
        """
        messages = state.values.get('messages', [])
        interrupts = self._parse_interrupts_to_response_objects(state.interrupts)
        return AgentStateResponse(messages=messages, interrupts=interrupts)

    async def _parse_request(self, request: AgentRequest) -> _ParsedAgentRequest:
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
            A _ParsedAgentRequest object containing either an AgentState or a Command,
            and an optional AgentResponse if there are interrupts in the state.
        """
        state = await self.get_state(request.thread_id)

        if state.interrupts:
            interrupts = self._parse_interrupts_to_response_objects(state.interrupts)
            if not request.input.commands:
                return _ParsedAgentRequest(
                    input=None,
                    response=AgentResponse(
                        message=AIMessage(content=self._default_interrupt_msg),
                        interrupts=interrupts,
                        thread_id=request.thread_id,
                    ),
                    interrupts=interrupts,
                )

            input_, missing = await self._get_resume_command_for_interrupts(
                interrupts=interrupts,
                commands=request.input.commands,
            )
            if missing:
                raise MissingInterruptCommandError(missing)

        else:
            query = request.input.query
            input_ = AgentState(messages=[HumanMessage(content=query)])

        return _ParsedAgentRequest(
            input=input_,
            response=None,
            interrupts=[],
        )

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
        messages: list[AnyMessage],
        interrupts: list[AgentToolInterrupt],
    ) -> None:
        """Creates or updates a conversation based on the request and response.

        If the conversation does not exist, it creates a new one. If it exists,
        it updates the conversation with the new message and any interrupts.
        """
        messages_to_add = get_messages_from_user_msg(messages)
        if not messages_to_add:
            return

        conversation = await self._conversation_repo.get_conversation(thread_id)
        if not conversation:
            conversation = await self._conversation_repo.create_conversation(
                pk=thread_id,
                user_id=user_id,
                title=str(messages_to_add[0].content)[:60]
                if isinstance(messages_to_add[0], HumanMessage)
                else 'Sin título',
            )

        last_index = len(messages_to_add) - 1
        for index, msg in enumerate(messages_to_add):
            if not isinstance(msg, LCMessage):
                continue
            await self._conversation_repo.add_message_to_conversation(
                conversation_id=conversation.id,
                lc_message=msg,
                interrupts=(interrupts or None) if index == last_index else None,
            )

    def _get_runnable_config(
        self,
        config_request: AgentConfig,
        context: Context | None = None,
    ) -> RunnableConfig:
        """Get the RunnableConfig for the agent.

        Args:
            config_request: The configuration request for the agent.
            context: The context of the agent. This is used to get the user ID for
                the Langfuse metadata. If not provided, the user ID will be None.
        """
        max_concurrency = (
            min(config_request.max_concurrency, settings.runnable.max_concurrency)
            if config_request.max_concurrency
            else settings.runnable.max_concurrency
        )

        recursion_limit = (
            min(config_request.recursion_limit, settings.runnable.max_recursion_limit)
            if config_request.recursion_limit
            else settings.runnable.max_recursion_limit
        )

        thread_id = str(config_request.thread_id)

        callbacks = []
        metadata = {}
        if settings.langfuse.enabled and langfuse_handler:
            callbacks.append(langfuse_handler)
            metadata = {
                'langfuse_user_id': context.user_id if context else DEFAULT_USER_ID,
                'langfuse_session_id': thread_id,
                'langfuse_tags': config_request.tags,
            }

        metadata.update(config_request.metadata)

        return RunnableConfig(
            configurable={
                'thread_id': thread_id,
            },
            run_name=self._graph.name,
            tags=config_request.tags,
            metadata=metadata,
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
    ) -> tuple[Command, list[str]]:
        """Get the resume command for the interrupts based on the commands provided.

        Args:
            interrupts: The list of interrupts that need to be resumed.
            commands: A dictionary of commands provided by the user,
                keyed by interrupt ID.

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

        return Command(resume={'decisions': decisions}), missing

    async def _resume_interrupts(
        self,
        interrupts: list[AgentToolInterrupt],
        commands: dict[str, AgentInterruptCommand],
        user_id: str | None = None,
    ) -> None:
        """Resume the interrupts based on the commands provided.

        Args:
            interrupts: The list of interrupts that need to be resumed.
            commands: A dictionary of commands provided by the user,
                keyed by interrupt ID.
            user_id: The ID of the user making the request. This is used to resume
                interrupts and update the conversation. If not provided, interrupts
                will not be resumed and the conversation will not be updated.
        """
        for interrupt in interrupts:
            command = commands[interrupt.id]
            await self._conversation_repo.resume_interrupt(
                execution_id=interrupt.id,
                command=command,
                reviewer_id=user_id,
            )
