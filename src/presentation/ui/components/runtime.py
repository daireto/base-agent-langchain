import asyncio
import threading
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from contextlib import AbstractAsyncContextManager
from inspect import iscoroutine
from queue import Queue
from typing import Any, ParamSpec, TypeVar

_STREAM_END = object()

R = TypeVar('R')
P = ParamSpec('P')


class RuntimeNotStartedError(RuntimeError):
    """Raised when trying to use the runtime before it has been started."""

    def __init__(self) -> None:
        super().__init__('Runtime is not started yet. Call start() first.')


class Runtime[T]:
    """Handler for running an asynchronous context manager in a synchronous environment.

    This class is useful in environments that are fundamentally synchronous, such
    as Streamlit apps, but still need to work with async resources. It opens an
    asynchronous context manager in a dedicated background thread, keeps its own
    event loop alive, and exposes two ways to interact with it:

    * ``submit`` schedules a coroutine on the runtime event loop and waits for
    its result.
    * ``consume`` schedules an async generator and yields its items back to the
    caller as synchronous values.

    Subclasses should override ``handle_ctx_value`` to process the value returned
    by ``__aenter__`` and initialize runtime-specific state from it. For example,
    an ``AgentRuntime`` can use that hook to create an ``AgentService`` from the
    resources exposed by the context manager. However, overriding ``handle_ctx_value``
    is not strictly necessary if the context manager does not produce any useful value.

    Examples:
        >>> class AgentRuntime(Runtime[AppResources]):
        ...     def handle_ctx_value(self, ctx_value: AppResources) -> None:
        ...         self._service = AgentService(
        ...             graph=ctx_value.graph,
        ...             conversation_repo=ctx_value.conversation_repo,
        ...         )
        >>> runtime = AgentRuntime()
        >>> runtime.start()
        >>> response = runtime.submit(service.invoke(request))
        >>> for event in runtime.consume(service.stream, request):
        ...     print(event)
    """

    def __init__(self, thread_name: str, ctx: AbstractAsyncContextManager[T]) -> None:
        """Initialize the runtime.

        Args:
            thread_name: The name assigned to the background thread.
            ctx: The asynchronous context manager that will be entered on startup.
        """
        self._ctx = ctx

        self.__thread = threading.Thread(
            target=self.__thread_main,
            daemon=True,
            name=thread_name,
        )
        self.__started = threading.Event()
        self.__loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        """Start the background thread and wait for the runtime to initialize.

        If the runtime has already started, this method does nothing.
        """
        if self.__started.is_set():
            return

        self.__thread.start()
        self.__started.wait()

    def stop(self) -> None:
        """Stop the runtime loop and close the async context manager.

        This method shuts down the background event loop and waits for the thread
        to finish its cleanup work.
        """
        if self.__loop is None:
            return

        future = asyncio.run_coroutine_threadsafe(
            self._shutdown(),
            self.__loop,
        )
        future.result(timeout=30)

        self.__loop.call_soon_threadsafe(self.__loop.stop)
        self.__thread.join(timeout=30)

    def handle_ctx_value(self, ctx_value: T) -> Any:
        """Handle the value returned by the async context manager.

        Subclasses should override this method to initialize runtime-specific
        resources from the value produced by ``__aenter__``. However, overriding
        this method is not strictly necessary if the context manager does not produce
        any useful value.

        Args:
            ctx_value: The value returned by the async context manager.

        Returns:
            An optional result from the initialization step.
        """

    def submit(self, coro: Coroutine[Any, Any, R]) -> R:
        """Submit a coroutine to the runtime event loop and wait for its result.

        Args:
            coro: The coroutine to execute on the runtime loop.

        Returns:
            The coroutine result.

        Raises:
            RuntimeError: If the runtime has not been started yet.
        """
        if self.__loop is None:
            raise RuntimeNotStartedError

        future = asyncio.run_coroutine_threadsafe(
            coro,
            self.__loop,
        )
        return future.result(timeout=30)

    def consume(
        self,
        generator_factory: Callable[P, AsyncGenerator[R]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Generator[R]:
        """Run an async generator on the runtime loop and yield its values.

        Args:
            generator_factory: A callable that returns an async generator.
            *args: Positional arguments forwarded to the generator factory.
            **kwargs: Keyword arguments forwarded to the generator factory.

        Yields:
            The items produced by the async generator.

        Raises:
            RuntimeError: If the runtime has not been started yet.
        """
        if self.__loop is None:
            raise RuntimeNotStartedError

        queue: Queue[Any] = Queue()

        async def producer() -> None:
            try:
                async for item in generator_factory(*args, **kwargs):
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

    async def _startup(self) -> None:
        """Enter the async context and initialize runtime state from it."""
        ctx_value = await self._ctx.__aenter__()
        result = self.handle_ctx_value(ctx_value)
        if iscoroutine(result):
            await result

    async def _shutdown(self) -> None:
        """Exit the async context manager and release runtime resources."""
        await self._ctx.__aexit__(None, None, None)

    def __thread_main(self) -> None:
        """Run the runtime event loop in the background thread."""
        self.__loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__loop)

        self.__loop.run_until_complete(self._startup())

        self.__started.set()
        self.__loop.run_forever()
