from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from typing_extensions import TypedDict


class SecurityHeaders(TypedDict):
    x_content_type_options: str
    x_frame_options: str
    referrer_policy: str
    strict_transport_security: str
    content_security_policy: str


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        hsts: bool = True,
        exclude_from_csp: list[str] | None = None,
        options: SecurityHeaders | None = None,
    ) -> None:
        super().__init__(app)
        self._hsts = hsts
        self._exclude_from_csp = self._strip_slash_in_list(exclude_from_csp or [])

        self._options = self._get_default_options()
        self._options.update(options or {})

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        path = request.url.path

        response.headers['X-Content-Type-Options'] = self._options[
            'x_content_type_options'
        ]
        response.headers['X-Frame-Options'] = self._options['x_frame_options']
        response.headers['Referrer-Policy'] = self._options['referrer_policy']

        if self._hsts:
            response.headers['Strict-Transport-Security'] = self._options[
                'strict_transport_security'
            ]

        if not self._check_excluded_from_csp(path):
            response.headers['Content-Security-Policy'] = self._options[
                'content_security_policy'
            ]

        return response

    def _check_excluded_from_csp(self, path: str) -> bool:
        return path.strip('/') in self._exclude_from_csp

    def _strip_slash_in_list(self, items: list[str]) -> list[str]:
        return [item.strip('/') for item in items]

    def _get_default_options(self) -> SecurityHeaders:
        return {
            'x_content_type_options': 'nosniff',
            'x_frame_options': 'DENY',
            'referrer_policy': 'no-referrer',
            'strict_transport_security': 'max-age=31536000; includeSubDomains',
            'content_security_policy': "default-src 'self'",
        }
