from collections.abc import Generator
from typing import Any

from langgraph.types import StateSnapshot

from dtos.common import SSEEvent
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
        self._service = None

    def invoke(self, request: AgentRequest) -> AgentResponse:
        return self.submit(self.service.invoke(request))

    def stream(self, request: AgentRequest) -> Generator[SSEEvent[AgentResponse]]:
        return self.consume(self.service.stream, request)

    def get_state(self, config: AgentConfig) -> StateSnapshot:
        return self.submit(self.service.get_state(config.thread_id))

    def clean_state(self, thread_id: str) -> None:
        return self.submit(self.service.clean_state(thread_id))

    def parse_state_to_response(self, state: StateSnapshot) -> AgentStateResponse:
        return self.service.parse_state_to_response(state)

    @property
    def service(self) -> AgentService:
        if self._service is None:
            raise RuntimeError('Runtime is not started yet. Call start() first.')

        return self._service

    def handle_ctx_value(self, ctx_value: AppResources) -> Any:
        self._service = AgentService(
            supervisor=ctx_value.supervisor,
            stream_transformer=ctx_value.stream_transformer,
            conversation_repo=ctx_value.conversation_repo,
        )


_runtime = AgentRuntime()
_runtime.start()


def get_runtime() -> AgentRuntime:
    return _runtime
