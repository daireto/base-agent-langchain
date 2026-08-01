from pydantic import Field

from dtos.base import ResponseDTO


class ServerHealthResponse(ResponseDTO):
    """Response model for server health check."""

    message: str = Field(..., description='"ok" if healthy, error message otherwise.')
    healthy: bool = Field(..., description='Health status')
