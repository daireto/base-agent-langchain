from collections.abc import AsyncGenerator
from typing import Any

from langchain.agents import AgentState
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.messages.ai import add_ai_message_chunks
from langchain_core.runnables import RunnableConfig
from langfuse.langchain import CallbackHandler
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import (
    Command,
    GraphOutput,
    Interrupt,
    StateSnapshot,
    StreamPart,
)

from core.config import settings
from core.context import Context
from core.definitions import LANGCHAIN_API_VERSION
from core.errors import MissingInterruptCommandError
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

langfuse_handler = CallbackHandler()


class AgentService:
    def __init__(
        self,
        graph: CompiledStateGraph[Any, Context | None, Any, Any],
        *,
        stream_transformer: BasePIIStreamTransformer,
    ) -> None:
        self.__graph = graph
        self._stream_transformer = stream_transformer

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
        input_, response = await self._parse_request(request)
        if response:
            return response

        response = await self.__graph.ainvoke(
            input_,
            config=self._get_runnable_config(request),
            context=context,
            version=LANGCHAIN_API_VERSION,
        )

        return self._parse_response(response)

    async def stream(
        self,
        request: AgentRequest,
        context: Context | None = None,
    ) -> AsyncGenerator[SSEEvent[AgentResponse]]:
        input_, response = await self._parse_request(request)
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
                stream_mode=['messages', 'values'],
                version=LANGCHAIN_API_VERSION,
            ):
                if event := self._parse_stream_part(
                    chunk, ai_msg_chunks_buffer, thread_id
                ):
                    yield event

            if flush := self._stream_transformer.flush_buffer(thread_id):
                yield SSEEvent(
                    event='chunk',
                    data=AgentResponse(message=flush),
                )

            state = await self.get_state(request)
            full_msg = state.values['messages'][-1]
            yield SSEEvent(event='end', data=AgentResponse(message=full_msg))

        finally:
            if request.thread_id:
                self._stream_transformer.drop_buffer(request.thread_id)

    async def get_state(self, config_request: AgentConfig) -> StateSnapshot:
        """Returns the current state of the thread."""
        return await self.__graph.aget_state(
            config=self._get_runnable_config(config_request)
        )

    async def clean_state(self, thread_id: str) -> None:
        """Cleans the state of the thread."""
        await self.__graph.checkpointer.adelete_thread(thread_id=thread_id)  # type: ignore

    def parse_state_to_response(self, state: StateSnapshot) -> AgentStateResponse:
        """Parses the state snapshot into a response object.

        Response contains messages and interrupts.
        """
        messages = state.values.get('messages', [])
        interrupts = self._parse_interrupts_to_response_objects(state.interrupts)
        return AgentStateResponse(messages=messages, interrupts=interrupts)

    async def _parse_request(
        self, request: AgentRequest
    ) -> tuple[AgentState | Command | None, AgentResponse | None]:
        state = await self.get_state(request)

        if state.interrupts:
            interrupts = self._parse_interrupts_to_response_objects(state.interrupts)
            if not request.input.commands:
                return None, AgentResponse(
                    message=self.default_interrupt_msg,
                    interrupts=interrupts,
                )

            input_, missing = self._get_resume_command_for_interrupts(
                interrupts, request.input.commands
            )
            if missing:
                raise MissingInterruptCommandError(missing)

        else:
            query = request.input.query
            input_ = AgentState(messages=[HumanMessage(content=query)])

        return input_, None

    def _parse_response(self, response: GraphOutput) -> AgentResponse:
        ai_msg = response.value['messages'][-1]

        if response.interrupts:
            interrupts = self._parse_interrupts_to_response_objects(response.interrupts)
            return AgentResponse(
                message=ai_msg if ai_msg.content else self.default_interrupt_msg,
                interrupts=interrupts,
            )

        return AgentResponse(message=ai_msg)

    def _parse_stream_part(
        self,
        chunk: StreamPart[Any, Any],
        ai_msg_chunks_buffer: list[AIMessageChunk],
        thread_id: str,
    ) -> SSEEvent[AgentResponse] | None:
        if chunk['type'] == 'messages':
            msg, metadata = chunk['data']
            if metadata.get('langgraph_node') not in ('model', 'tools'):
                return None

            if (
                isinstance(msg, AIMessageChunk)
                and not msg.content
                and msg.tool_call_chunks
            ):
                ai_msg_chunks_buffer.append(msg)
                return None

            if ai_msg_chunks_buffer:
                ai_msg = add_ai_message_chunks(*ai_msg_chunks_buffer)
                ai_msg_chunks_buffer.clear()
                return SSEEvent(
                    event='chunk',
                    data=AgentResponse(message=ai_msg),
                )

            if msg := self._stream_transformer.transform_stream_chunk(msg, thread_id):
                return SSEEvent(
                    event='chunk',
                    data=AgentResponse(message=msg),
                )

        elif chunk['type'] == 'values' and chunk['interrupts']:
            msg = self.default_interrupt_msg
            if flush := self._stream_transformer.flush_buffer(thread_id):
                msg = flush

            interrupts = self._parse_interrupts_to_response_objects(chunk['interrupts'])
            return SSEEvent(
                event='interrupts',
                data=AgentResponse(message=msg, interrupts=interrupts),
            )

        return None

    def _get_runnable_config(self, config_request: AgentConfig) -> RunnableConfig:
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
                        name=action_request['name'],
                        args=action_request['args'],
                        description=action_request['description'].split('\n', 1)[0],
                        allowed_decisions=review_config['allowed_decisions'],
                    )
                )
        return response_interrupts

    def _get_resume_command_for_interrupts(
        self,
        interrupts: list[AgentToolInterrupt],
        commands: dict[str, AgentInterruptCommand],
    ) -> tuple[Command, list[str]]:
        decisions = []
        missing = []

        for interrupt in interrupts:
            command = commands.get(interrupt.name)
            if not command:
                missing.append(interrupt.name)
                continue

            if command.decision == 'approve':
                decisions.append({'type': 'approve'})

            elif command.decision == 'edit':
                if not command.edited_action:
                    raise ValueError(
                        f'Edited action is required for interrupt {interrupt.name}'
                    )

                decisions.append(
                    {
                        'type': 'edit',
                        'edited_action': {
                            'name': command.edited_action.name,
                            'args': command.edited_action.args,
                        },
                    }
                )

            elif command.decision == 'reject':
                decisions.append(
                    {
                        'type': 'reject',
                        'message': command.reject_reason
                        or 'User rejected this action. Do not retry this tool call.',
                    }
                )

        return Command(resume={'decisions': decisions}), missing
