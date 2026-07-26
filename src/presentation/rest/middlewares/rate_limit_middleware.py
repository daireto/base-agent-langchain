import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from limits import RateLimitItem, WindowStats, parse_many
from limits.aio.strategies import FixedWindowRateLimiter
from limits.storage import StorageTypes, storage_from_string
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp
from starlette.websockets import WebSocket

TZ = datetime.now().astimezone().tzinfo


@dataclass
class RateLimitResult:
    """Results of a rate limit check."""

    is_allowed: bool
    """Indicates whether the request is allowed based on the rate limit check."""

    rate_limit: str
    """The rate limit information in the format:
    granularity;r=remaining;t=reset_time.
    """

    retry_after: int | None = None
    """The time in seconds after which the client can retry the request
    if it was rate-limited.
    """

    violated_policies: list[str] | None = None
    """List of violated rate limit policies if the request was rate-limited."""

    def __bool__(self) -> bool:
        return self.is_allowed


def get_longest_prefix_match(prefixes: list[str], path: str) -> str:
    """Get the longest matching prefix from a list of prefixes for a given path.

    Args:
        prefixes: A list of prefixes to match against the path.
        path: The path to check for matching prefixes.

    Returns:
        The longest matching prefix if found, otherwise '/'.
    """

    def matches(path: str, prefix: str) -> bool:
        return path == prefix or path.startswith(prefix + '/')

    for prefix in prefixes:
        if matches(path, prefix):
            return prefix

    return '/'


async def default_identifier(request: Request | WebSocket) -> str:
    """Get the default identifier for rate limiting.

    Default implementation uses the client's IP address and the request path
    as the identifier.

    Args:
        request: The incoming request or WebSocket connection.

    Returns:
        A string identifier for rate limiting, combining the client's IP
        address and the request path.
    """
    if forwarded := request.headers.get('X-Forwarded-For'):
        ip = forwarded.split(',')[0]
    elif request.client:
        ip = request.client.host
    else:
        ip = '127.0.0.1'
    return ip + ':' + request.scope['path']


async def default_callback(_: Request, result: RateLimitResult) -> Response:
    """Generate a default response for rate-limited requests.

    Args:
        _: The incoming request that was rate-limited.
        result: The result of the rate limit check, containing information
            about the violated policies.

    Returns:
        A JSONResponse with status code 429 (Too Many Requests) and details
        about the rate limit violation.
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            'type': 'https://iana.org/assignments/http-problem-types#abnormal-usage-detected',
            'title': 'Abnormal Usage Detected',
            'status': status.HTTP_429_TOO_MANY_REQUESTS,
            'detail': 'Request not satisfied due to detection of abnormal request pattern',
            'violated-policies': result.violated_policies,
        },
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting incoming requests.

    Attributes:
        _storage: The storage backend for rate limiting.
        _limiter: The rate limiter instance.
        _root_limit: The default rate limit for requests.
        _prefix_limits: A dictionary mapping path prefixes to specific rate limits.
        _sorted_prefixes: A list of path prefixes sorted by length in descending order.
        _identifier: A callable to extract the identifier for rate limiting
            from the request.
        _callback: A callable to generate a response for rate-limited requests.
        _skip: A list of paths or a callable to determine which requests to skip
            for rate limiting.
    """

    def __init__(
        self,
        app: ASGIApp,
        storage_uri: str,
        root_limit: str,
        prefix_limits: dict[str, str] | None = None,
        identifier: Callable[[Request | WebSocket], Awaitable[str]] | None = None,
        callback: Callable[[Request, RateLimitResult], Awaitable[Response]]
        | None = None,
        skip: list[str] | Callable[[Request], Awaitable[bool]] | None = None,
    ) -> None:
        """Initialize the RateLimitMiddleware.

        Args:
            app: The ASGI application to wrap.
            storage_uri: The URI of the storage backend for rate limiting.
            root_limit: The default rate limit for requests.
            prefix_limits: A dictionary mapping path prefixes to specific rate limits.
                Defaults to None.
            identifier: A callable to extract the identifier for rate limiting
                from the request. Defaults to None.
            callback: A callable to generate a response for rate-limited requests.
                Defaults to None.
            skip: A list of paths or a callable to determine which requests to skip
                for rate limiting. Defaults to None.
        """
        super().__init__(app)
        self._storage = self._storage_from_string(storage_uri)
        self._limiter = FixedWindowRateLimiter(self._storage)

        self._root_limit = root_limit
        self._prefix_limits = self._normalize_prefixes(prefix_limits or {})
        self._sorted_prefixes = self._get_sorted_prefixes(self._prefix_limits)

        self._identifier = identifier or default_identifier
        self._callback = callback or default_callback

        if isinstance(skip, list):
            self._skip = [path.strip('/') for path in skip]
        else:
            self._skip = skip

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Apply the configured rate limiting rules to the incoming request.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint to invoke.

        Returns:
            The downstream response, optionally wrapped by a rate limit callback.
        """
        if await self._check_skip(request):
            return await call_next(request)

        limit_str = self.resolve_limit(request.url.path)
        rate_limits = self._parse_limit_string(limit_str)
        identifier = await self._identifier(request)
        result = await self._consume_rate_limits(rate_limits, identifier)

        if result:
            response = await call_next(request)
        else:
            response = await self._callback(request, result)

        self._add_headers(response, result, rate_limits)

        return response

    def resolve_limit(self, path: str) -> str:
        """Resolve the applicable rate-limit policy for a path.

        Args:
            path: The request path to evaluate.

        Returns:
            The rate limit string for the matching route prefix or the root limit.
        """
        prefix = get_longest_prefix_match(
            prefixes=self._sorted_prefixes,
            path=path.lstrip('/'),
        )
        return self._prefix_limits.get(prefix, self._root_limit)

    async def _consume_rate_limits(
        self, rate_limits: list[RateLimitItem], identifier: str
    ) -> RateLimitResult:
        """Consume rate limit tokens for the given identifier and policies.

        Args:
            rate_limits: The rate limit policies to evaluate.
            identifier: The client identifier used for tracking limits.

        Returns:
            The result describing whether the request is allowed and the applied policy.
        """
        less_restrictive_limit_window = None
        violated_limits = []

        for limit in rate_limits:
            is_allowed = await self._limiter.hit(limit, identifier)
            window = await self._limiter.get_window_stats(limit, identifier)
            reset_time = self._get_window_reset_seconds(window)

            if not is_allowed:
                violated_limits.append((limit, window.remaining, reset_time))
                continue

            if not less_restrictive_limit_window:
                less_restrictive_limit_window = (
                    limit.GRANULARITY.name,
                    window.remaining,
                    reset_time,
                )

        if violated_limits:
            limit, remaining, reset_time = violated_limits[0]
            return RateLimitResult(
                is_allowed=False,
                rate_limit=f'"{limit.GRANULARITY.name}";r={remaining};t={reset_time}',
                retry_after=reset_time,
                violated_policies=[v[0].GRANULARITY.name for v in violated_limits],
            )

        name, remaining, reset_time = less_restrictive_limit_window or (
            'default',
            0,
            0,
        )
        return RateLimitResult(
            is_allowed=True,
            rate_limit=f'"{name}";r={remaining};t={reset_time}',
        )

    def _get_rate_limit_policy(self, rate_limits: list[RateLimitItem]) -> str:
        """Build the policy header value for the provided rate limits.

        Args:
            rate_limits: The rate limit policies to serialize.

        Returns:
            The formatted policy string for the response headers.
        """
        return ','.join(
            f'"{limit.GRANULARITY.name}";q={limit.amount};w={limit.get_expiry()}'
            for limit in rate_limits
        )

    def _add_headers(
        self,
        response: Response,
        result: RateLimitResult,
        rate_limits: list[RateLimitItem],
    ) -> None:
        """Attach rate limit metadata headers to the response.

        Args:
            response: The response object to update.
            result: The rate limit evaluation result.
            rate_limits: The policies used to evaluate the request.
        """
        response.headers['RateLimit-Policy'] = self._get_rate_limit_policy(rate_limits)
        response.headers['RateLimit-Limit'] = result.rate_limit
        if result.retry_after:
            response.headers['Retry-After'] = str(result.retry_after)

    def _get_window_reset_seconds(self, window: WindowStats) -> int:
        """Calculate the number of seconds until the current window resets.

        Args:
            window: The current rate limit window statistics.

        Returns:
            The remaining time in seconds before the window resets.
        """
        reset_time_delta = datetime.fromtimestamp(
            window.reset_time, tz=TZ
        ) - datetime.now(tz=TZ)
        return math.ceil(reset_time_delta.total_seconds())

    def _storage_from_string(self, storage_uri: str) -> StorageTypes:
        """Create a storage backend instance from a connection URI.

        Args:
            storage_uri: The storage backend URI.

        Returns:
            The initialized storage backend.
        """
        if not storage_uri.startswith('async+'):
            storage_uri = 'async+' + storage_uri

        options = {}
        if storage_uri.startswith('async+redis'):
            options['implementation'] = 'redispy'

        return storage_from_string(storage_uri, **options)

    def _parse_limit_string(self, limit_string: str) -> list[RateLimitItem]:
        """Parse a limit string into ordered rate limit items.

        Args:
            limit_string: The limit definition string.

        Returns:
            A sorted list of parsed rate limit items.
        """
        return sorted(parse_many(limit_string), key=lambda limit: limit.amount)

    def _normalize_prefixes(self, prefix_limits: dict[str, str]) -> dict[str, str]:
        """Normalize prefix-based limits by stripping leading slashes.

        Args:
            prefix_limits: The mapping of path prefixes to rate limit strings.

        Returns:
            A normalized dictionary of prefix limits.
        """
        return {
            prefix.lstrip('/').strip(): limit for prefix, limit in prefix_limits.items()
        }

    def _get_sorted_prefixes(self, endpoint_limits: dict[str, str]) -> list[str]:
        """Return path prefixes sorted by descending length.

        Args:
            endpoint_limits: The mapping of prefixes to rate limit strings.

        Returns:
            A list of prefixes ordered from longest to shortest.
        """
        sorted_prefixes = sorted(endpoint_limits.keys(), key=len, reverse=True)
        return [prefix for prefix in sorted_prefixes if prefix.lstrip('/') != '']

    async def _check_skip(self, request: Request) -> bool:
        """Determine whether the request should bypass rate limiting.

        Args:
            request: The incoming HTTP request.

        Returns:
            True when the request should be skipped.
        """
        if not self._skip:
            return False

        if callable(self._skip):
            return await self._skip(request)

        return request.url.path.strip('/') in self._skip
