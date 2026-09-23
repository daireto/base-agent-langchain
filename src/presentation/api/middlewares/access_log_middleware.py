import logging
import time
from collections.abc import Callable

from asgi_correlation_id.context import correlation_id
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from structlog.stdlib import BoundLogger


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Middleware for logging access requests and responses.

    Attributes:
        _logger: The logger instance for logging access requests and responses.
        _excluded_path_prefixes: The path prefixes to exclude from access logging.
        _user_id_extractor: A callable to extract the user ID from the request.
    """

    def __init__(
        self,
        app: ASGIApp,
        logger: BoundLogger,
        excluded_path_prefixes: str | list[str] | None = None,
        user_id_extractor: Callable[[Request], str] | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
            logger: The logger instance for logging access requests and responses.
            excluded_path_prefixes: The path prefixes to exclude from access logging.
                Defaults to None.
            user_id_extractor: A callable to extract the user ID from the request.
                Defaults to None.
        """
        super().__init__(app)
        self._logger = logger
        self._excluded_path_prefixes = self._normalize_path_prefixes(
            excluded_path_prefixes or ''
        )
        self._user_id_extractor = user_id_extractor or self._default_user_id_extractor

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Handle an incoming request and log its outcome.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint to invoke.

        Returns:
            The response returned by the downstream application.
        """
        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as e:
            await self._access_log(
                request=request,
                duration_ms=(time.time() - start_time) * 1000,
                exception=e,
            )
            raise

        await self._access_log(
            request=request,
            duration_ms=(time.time() - start_time) * 1000,
            response=response,
        )

        return response

    async def _access_log(
        self,
        request: Request,
        duration_ms: float,
        response: Response | None = None,
        exception: Exception | None = None,
    ) -> None:
        """Log the outcome of a request based on its response or exception.

        Args:
            request: The incoming HTTP request.
            duration_ms: The elapsed request duration in milliseconds.
            response: The response returned by the downstream application, if any.
            exception: The exception raised during request handling, if any.
        """
        if self._check_excluded_path(request.url.path):
            return

        status_code = (
            response.status_code if response else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        if status_code == status.HTTP_404_NOT_FOUND and not exception:
            return

        request_failed = exception or status_code >= status.HTTP_400_BAD_REQUEST
        self._logger.log(
            logging.ERROR if request_failed else logging.INFO,
            'Request failed' if request_failed else 'Request succeeded',
            **self._get_log_data(request, status_code, duration_ms, exception),
        )

    def _get_log_data(
        self,
        request: Request,
        status_code: int,
        duration_ms: float,
        exception: Exception | None,
    ) -> dict[str, str | int | float | None]:
        """Build the structured log payload for a request.

        Args:
            request: The incoming HTTP request.
            status_code: The HTTP status code for the response.
            duration_ms: The elapsed request duration in milliseconds.
            exception: The exception raised during request handling, if any.

        Returns:
            A dictionary with the log fields for the request.
        """
        log_data = {
            'request_id': correlation_id.get(),
            'method': request.method,
            'path': request.url.path,
            'query': request.url.query,
            'protocol': request.scope.get('scheme', 'http'),
            'status_code': status_code,
            'duration_ms': duration_ms,
            'user_id': self._user_id_extractor(request),
            'trace_id': request.headers.get('x-trace-id'),
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'referrer': request.headers.get('referer'),
            'exception': str(exception) if exception else None,
        }

        if self._check_redirect(status_code):
            log_data['location'] = request.headers.get('location')

        return log_data

    def _check_redirect(self, status_code: int) -> bool:
        """Return whether the status code indicates a redirect response.

        Args:
            status_code: The HTTP status code to evaluate.

        Returns:
            True if the status code corresponds to a redirect response.
        """
        return (
            status.HTTP_300_MULTIPLE_CHOICES
            <= status_code
            < status.HTTP_400_BAD_REQUEST
        )

    def _check_excluded_path(self, path: str) -> bool:
        """Return whether the path should be excluded from access logging.

        Args:
            path: The request path to evaluate.

        Returns:
            True if the path matches an excluded prefix.
        """
        if not path.startswith('/'):
            path = '/' + path

        return path.startswith(self._excluded_path_prefixes)

    def _normalize_path_prefixes(self, prefixes: str | list[str]) -> tuple[str, ...]:
        """Normalize path prefixes into a tuple with leading slashes.

        Args:
            prefixes: A string or list of prefixes to normalize.

        Returns:
            A tuple of normalized path prefixes.
        """
        if not prefixes:
            return ()

        if isinstance(prefixes, str):
            prefixes = prefixes.split(',')

        normalized = [
            prefix if prefix.startswith('/') else f'/{prefix}' for prefix in prefixes
        ]

        return tuple(normalized)

    def _default_user_id_extractor(self, request: Request) -> str | None:
        """Extract the user ID from the request headers.

        Args:
            request: The incoming HTTP request.

        Returns:
            The user ID from the request headers, if present.
        """
        return request.headers.get('x-user-id')
