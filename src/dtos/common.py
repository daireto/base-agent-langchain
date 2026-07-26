from typing import Literal

from pydantic import BaseModel, field_serializer


class SSEEvent[T: BaseModel](BaseModel):
    """Server-Sent Event (SSE) model for streaming data to clients."""

    event: Literal['chunk', 'end']
    data: T

    @field_serializer('data', when_used='json')
    def serialize_data(self, data: T) -> str:
        return data.model_dump_json()
