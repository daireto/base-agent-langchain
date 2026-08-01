from typing import Literal

from pydantic import BaseModel, Field, field_serializer

from dtos.base import ResponseDTO


class Pagination[T: ResponseDTO](BaseModel):
    """Pagination model for API responses."""

    items: list[T] = Field(..., description='The list of items for the current page.')
    page: int = Field(..., description='The current page number.')
    size: int = Field(..., description='The number of items per page.')
    total: int = Field(..., description='The total number of items.')
    total_pages: int = Field(..., description='The total number of pages.')


class SSEEvent[T: ResponseDTO](BaseModel):
    """Server-Sent Event (SSE) model for streaming data to clients."""

    event: Literal['chunk', 'end'] = Field(
        ..., description='The type of the SSE event.'
    )
    data: T = Field(..., description='The data associated with the SSE event.')

    @field_serializer('data', when_used='json')
    def serialize_data(self, data: T) -> str:
        return data.model_dump_json()
