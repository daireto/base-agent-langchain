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
    def __init__(
        self,
        app: ASGIApp,
        logger: BoundLogger,
        excluded_path_prefixes: str | list[str] | None = None,
        user_id_extractor: Callable[[Request], str] | None = None,
    ) -> None:
        super().__init__(app)
        self._logger = logger
        self._excluded_path_prefixes = self.__normalize_path_prefixes(
            excluded_path_prefixes or ''
        )
        self._user_id_extractor = user_id_extractor or self.__default_user_id_extractor

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as e:
            await self.__access_log(
                request=request,
                duration_ms=(time.time() - start_time) * 1000,
                exception=e,
            )
            raise

        await self.__access_log(
            request=request,
            duration_ms=(time.time() - start_time) * 1000,
            response=response,
        )

        return response

    async def __access_log(
        self,
        request: Request,
        duration_ms: float,
        response: Response | None = None,
        exception: Exception | None = None,
    ) -> None:
        if self.__check_excluded_path(request.url.path):
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
            **self.__get_log_data(request, status_code, duration_ms, exception),
        )

    def __get_log_data(
        self,
        request: Request,
        status_code: int,
        duration_ms: float,
        exception: Exception | None,
    ) -> dict[str, str | int | float | None]:
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

        if self.__check_redirect(status_code):
            log_data['location'] = request.headers.get('location')

        return log_data

    def __check_redirect(self, status_code: int) -> bool:
        return (
            status.HTTP_300_MULTIPLE_CHOICES
            <= status_code
            < status.HTTP_400_BAD_REQUEST
        )

    def __check_excluded_path(self, path: str) -> bool:
        if not path.startswith('/'):
            path = '/' + path

        return path.startswith(self._excluded_path_prefixes)

    def __normalize_path_prefixes(self, prefixes: str | list[str]) -> tuple[str, ...]:
        if not prefixes:
            return ()

        if isinstance(prefixes, str):
            prefixes = prefixes.split(',')

        normalized = [
            prefix if prefix.startswith('/') else f'/{prefix}' for prefix in prefixes
        ]

        return tuple(normalized)

    def __default_user_id_extractor(self, request: Request) -> str | None:
        return request.headers.get('x-user-id')
