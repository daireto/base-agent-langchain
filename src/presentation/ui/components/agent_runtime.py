from collections.abc import Generator
from typing import Any

from langgraph.types import StateSnapshot
from uuid_utils.compat import UUID

from agents.context import Context
from core.definitions import DEFAULT_USER_ID
from dtos.common import SSEEvent
from persistence.models import Conversation
from persistence.parsers.message_parsers import LCMessage
from persistence.repos.base_conversation_repository import BaseConversationRepository
from presentation.ui.components.runtime import Runtime
from services.agent_service import (
    AgentConfig,
    AgentRequest,
    AgentResponse,
    AgentService,
    AgentStateResponse,
)
from setup import AppResources, setup


class AgentRuntime(Runtime[AppResources]):
    def __init__(self) -> None:
        super().__init__(thread_name='AgentRuntimeThread', ctx=setup())
        self._agent_service = None
        self._conversation_repo = None

    def invoke(self, request: AgentRequest) -> AgentResponse:
        return self.submit(
            self.agent_service.invoke(request, Context(user_id=DEFAULT_USER_ID))
        )

    def stream(self, request: AgentRequest) -> Generator[SSEEvent[AgentResponse]]:
        return self.consume(
            self.agent_service.stream, request, Context(user_id=DEFAULT_USER_ID)
        )

    def get_state(self, config: AgentConfig) -> StateSnapshot:
        return self.submit(self.agent_service.get_state(config.thread_id))

    def clean_state(self, thread_id: UUID) -> None:
        return self.submit(self.agent_service.clean_state(thread_id))

    def parse_state_to_response(self, state: StateSnapshot) -> AgentStateResponse:
        return self.agent_service.parse_state_to_response(state)

    def get_lc_messages(self, thread_id: UUID) -> list[LCMessage]:
        return self.submit(self.conversation_repo.get_lc_messages(thread_id))

    def get_conversations(
        self, user_id: str | None = None, limit: int = 100, skip: int = 0
    ) -> list[Conversation]:
        return self.submit(
            self.conversation_repo.get_conversations(
                user_id=user_id,
                limit=limit,
                skip=skip,
                with_count=False,
            )
        )

    def delete_conversation(self, thread_id: UUID) -> None:
        return self.submit(self.conversation_repo.delete_conversation(thread_id))

    @property
    def agent_service(self) -> AgentService:
        if self._agent_service is None:
            raise RuntimeError('Runtime is not started yet. Call start() first.')

        return self._agent_service

    @property
    def conversation_repo(self) -> BaseConversationRepository:
        if self._conversation_repo is None:
            raise RuntimeError('Runtime is not started yet. Call start() first.')

        return self._conversation_repo

    def handle_ctx_value(self, ctx_value: AppResources) -> Any:
        self._agent_service = AgentService(
            supervisor=ctx_value.supervisor,
            stream_transformer=ctx_value.stream_transformer,
            conversation_repo=ctx_value.conversation_repo,
        )
        self._conversation_repo = ctx_value.conversation_repo


_runtime = AgentRuntime()
_runtime.start()


def get_runtime() -> AgentRuntime:
    return _runtime
