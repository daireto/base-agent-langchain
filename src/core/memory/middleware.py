from collections.abc import Awaitable, Callable
from typing import Any, override

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ExtendedModelResponse,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain.messages import AnyMessage, SystemMessage
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from core.definitions import DEFAULT_USER_ID
from core.memory.extractor.base_memory_extractor import BaseMemoryExtractor
from core.memory.store.base_memory_store import BaseMemoryStore
from utils.messages import get_last_user_message


class MemoryMiddleware(AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]):
    """Integrate memory retrieval and storage into the agent's execution flow.

    This middleware retrieves relevant memories before the model is invoked and saves
    new memories after the model generates a response.

    Attributes:
        _memory_store: The memory store used to save and retrieve memories.
        _memory_extractor: The memory extractor used to extract memories from messages.
        _system_prompt: The system prompt template used to format the memory context.
    """

    def __init__(
        self,
        memory_store: BaseMemoryStore,
        memory_extractor: BaseMemoryExtractor,
        system_prompt: str,
    ) -> None:
        """Initialize the MemoryMiddleware.

        Args:
            memory_store: The memory store used to save and retrieve memories.
            memory_extractor: The memory extractor used to extract memories
                from messages.
            system_prompt: The system prompt template used to format the memory context.
        """
        self._memory_store = memory_store
        self._memory_extractor = memory_extractor
        self._system_prompt = system_prompt

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[
            [ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]
        ],
    ) -> ModelResponse[ResponseT] | AIMessage | ExtendedModelResponse[ResponseT]:
        if not request.system_message:
            return await handler(request)

        if not request.messages:
            return await handler(request)

        if memory_context := await self._search_and_get_memories(
            request.messages, request.runtime
        ):
            system_msg = SystemMessage(
                self._system_prompt.format(memory_context=memory_context)
            )
            return await handler(request.override(system_message=system_msg))

        return await handler(request)

    @override
    async def aafter_model(
        self, state: AgentState[Any], runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        messages = state['messages']
        if not messages:
            return None

        await self._extract_and_save_memories(messages, runtime)

    async def _search_and_get_memories(
        self, messages: list[AnyMessage], runtime: Runtime[ContextT]
    ) -> str | None:
        """Search for relevant memories and format them as a string.

        Args:
            messages: The current messages in the conversation.
            runtime: The runtime of the agent execution.

        Returns:
            A formatted string of relevant memories. None if no memories are found.
        """
        user_id = self._get_user_id(runtime)

        last_user_msg, last_user_idx = get_last_user_message(messages)
        if not last_user_msg or last_user_idx is None:
            return None

        memories = await self._memory_store.search(
            user_id=user_id,
            query=str(last_user_msg.content),
        )
        return '\n'.join(f'- {memory}' for memory in memories[:20])

    async def _extract_and_save_memories(
        self, messages: list[AnyMessage], runtime: Runtime[ContextT]
    ) -> None:
        """Extract and save memories from the latest user message.

        Args:
            messages: The current messages in the conversation.
            runtime: The runtime of the agent execution.
        """
        user_id = self._get_user_id(runtime)

        last_user_msg, last_user_idx = get_last_user_message(messages)
        if not last_user_msg or last_user_idx is None:
            return

        if memories := await self._memory_extractor.extract([last_user_msg]):
            await self._memory_store.save(
                user_id=user_id,
                memories=memories,
            )

    def _get_user_id(self, runtime: Runtime[ContextT]) -> str:
        """Get the user ID from the runtime context."""
        return getattr(runtime.context, 'user_id', DEFAULT_USER_ID)
