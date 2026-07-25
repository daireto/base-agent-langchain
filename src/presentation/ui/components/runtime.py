import asyncio
import threading
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from queue import Queue
from typing import Any

from langgraph.types import StateSnapshot
from uuid_utils.compat import UUID

from agents.supervisor import Supervisor
from dtos.common import SSEEvent
from services.agent_service import (
    AgentConfig,
    AgentRequest,
    AgentResponse,
    AgentService,
    AgentStateResponse,
)
from setup import Resources, setup

_STREAM_END = object()


@dataclass(slots=True)
class RuntimeState:
    context: AbstractAsyncContextManager[tuple[Supervisor, Resources]]


class AgentRuntime:
    def __init__(self) -> None:
        self.__thread = threading.Thread(
            target=self._thread_main,
            daemon=True,
            name='AgentRuntime',
        )
        self.__started = threading.Event()
        self.__loop: asyncio.AbstractEventLoop | None = None
        self.__runtime: RuntimeState | None = None
        self.__service: AgentService | None = None

    def start(self) -> None:
        if self.__started.is_set():
            return

        self.__thread.start()
        self.__started.wait()

    def stop(self) -> None:
        if self.__loop is None:
            return

        future = asyncio.run_coroutine_threadsafe(
            self._shutdown(),
            self.__loop,
        )
        future.result(timeout=30)

        self.__loop.call_soon_threadsafe(self.__loop.stop)
        self.__thread.join(timeout=30)

    def invoke(self, request: AgentRequest) -> AgentResponse:
        return self._submit(self._service.invoke(request))

    def stream(self, request: AgentRequest) -> Generator[SSEEvent[AgentResponse]]:
        return self._consume(lambda: self._service.stream(request))

    def get_state(self, config: AgentConfig) -> StateSnapshot:
        return self._submit(self._service.get_state(config))

    def clean_state(self, thread_id: UUID) -> None:
        return self._submit(self._service.clean_state(thread_id))

    def parse_state_to_response(self, state: StateSnapshot) -> AgentStateResponse:
        return self._service.parse_state_to_response(state)

    @property
    def _service(self) -> AgentService:
        if self.__service is None:
            raise RuntimeError('Runtime is not started yet. Call start() first.')

        return self.__service

    async def _startup(self) -> None:
        ctx = setup()
        supervisor, resources = await ctx.__aenter__()
        self.__runtime = RuntimeState(context=ctx)
        self.__service = AgentService(
            supervisor=supervisor,
            stream_transformer=resources.stream_transformer,
            conversation_repo=resources.conversation_repo,
        )

    async def _shutdown(self) -> None:
        if self.__runtime is None:
            return
        await self.__runtime.context.__aexit__(None, None, None)

    def _submit(self, coro: Coroutine) -> Any:
        if self.__loop is None:
            raise RuntimeError('Runtime is not started yet. Call start() first.')

        future = asyncio.run_coroutine_threadsafe(
            coro,
            self.__loop,
        )
        return future.result(timeout=30)

    def _consume(
        self,
        generator_factory: Callable[[], AsyncGenerator[Any]],
    ) -> Generator[Any]:
        if self.__loop is None:
            raise RuntimeError('Runtime is not started yet. Call start() first.')

        queue: Queue[Any] = Queue()

        async def producer() -> None:
            try:
                async for item in generator_factory():
                    queue.put(item)

            except Exception as exc:
                queue.put(exc)

            finally:
                queue.put(_STREAM_END)

        asyncio.run_coroutine_threadsafe(
            producer(),
            self.__loop,
        )

        while True:
            item = queue.get()

            if item is _STREAM_END:
                break

            if isinstance(item, Exception):
                raise item

            yield item

    def _thread_main(self) -> None:
        self.__loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__loop)

        self.__loop.run_until_complete(self._startup())

        self.__started.set()
        self.__loop.run_forever()


_runtime = AgentRuntime()
_runtime.start()


def get_runtime() -> AgentRuntime:
    return _runtime
