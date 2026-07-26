from pydantic import BaseModel, Field


class MemoriesResponse(BaseModel):
    """Represents the response for user memories."""

    user_id: str = Field(..., description='User ID associated with the memories')
    memories: list[str] = Field(..., description='List of user memories')
