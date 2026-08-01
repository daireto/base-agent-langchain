from abc import ABC
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from uuid_utils.compat import UUID


class BaseDTO(BaseModel, ABC):
    pass


class RequestDTO(BaseDTO, ABC):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ResponseDTO(BaseDTO, ABC):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class EntityResponseDTO(ResponseDTO, ABC):
    id: UUID = Field(..., description='Unique identifier of the entity')
    created_at: datetime = Field(
        ..., description='Datetime when the entity was created'
    )
    updated_at: datetime = Field(
        ..., description='Datetime when the entity was last updated'
    )
