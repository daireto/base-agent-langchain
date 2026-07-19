from pydantic import BaseModel, Field


class ServerHealthResponse(BaseModel):
    message: str = Field(..., description='"ok" if healthy, error message otherwise.')
    healthy: bool = Field(..., description='Health status')
