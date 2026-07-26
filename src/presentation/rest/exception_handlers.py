from asgi_correlation_id import correlation_id
from fastapi import HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.utils import is_body_allowed_for_status_code
from pydantic import ValidationError

from core.errors import Error, ErrorCode
from utils.rfc_9457 import (
    build_rfc_9457_fastapi_response,
    error_to_rfc_9457_response,
)


def get_correlation_id_header() -> dict[str, str]:
    """Get the X-Request-ID header for the current request.

    Returns:
        A dictionary containing the correlation ID header.
    """
    return {'X-Request-ID': correlation_id.get() or ''}


def get_correlation_id_urn() -> str | None:
    """Get the correlation ID as a URN for the current request.

    Returns:
        A string representing the correlation ID in URN format,
            or None if not available.
    """
    if req_id := correlation_id.get():
        return f'urn:uuid:{req_id}'
    return None


async def http_exception_handler(_: Request, exc: HTTPException) -> Response:
    """Handle HTTP exceptions and return a structured RFC 9457 response."""
    headers = getattr(exc, 'headers', {}) or {}
    headers.update(get_correlation_id_header())
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=headers)
    return build_rfc_9457_fastapi_response(
        title=exc.detail,
        status=exc.status_code,
        detail=exc.detail,
        code=ErrorCode.UNEXPECTED_ERROR,
        instance=get_correlation_id_urn(),
        headers=headers,
    )


async def request_validation_exception_handler(
    _: Request, exc: RequestValidationError | ValidationError
) -> Response:
    """Handle request validation errors and return a structured RFC 9457 response."""
    return build_rfc_9457_fastapi_response(
        title='Validation Error',
        status=422,
        detail='Invalid input.',
        code=ErrorCode.VALIDATION_ERROR,
        instance=get_correlation_id_urn(),
        errors=exc.errors(),
        headers=get_correlation_id_header(),
    )


async def domain_exception_handler(_: Request, exc: Error) -> Response:
    """Handle domain-specific errors and return a structured RFC 9457 response."""
    return error_to_rfc_9457_response(
        exc,
        instance=get_correlation_id_urn(),
        headers=get_correlation_id_header(),
    )


async def unexpected_exception_handler(_: Request, __: Exception) -> Response:
    """Handle unexpected exceptions and return a structured RFC 9457 response."""
    return build_rfc_9457_fastapi_response(
        title='Internal Server Error',
        status=500,
        detail='An unexpected error occurred. Please try again later.',
        code=ErrorCode.UNEXPECTED_ERROR,
        instance=get_correlation_id_urn(),
        headers=get_correlation_id_header(),
    )


exception_handlers = {
    HTTPException: http_exception_handler,
    RequestValidationError: request_validation_exception_handler,
    ValidationError: request_validation_exception_handler,
    Error: domain_exception_handler,
    Exception: unexpected_exception_handler,
}
