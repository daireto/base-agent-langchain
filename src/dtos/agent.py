from typing import Any, Literal

from langchain_core.messages import AnyMessage, BaseMessage
from pydantic import Field
from uuid_utils.compat import UUID

from dtos.base import RequestDTO, ResponseDTO
from utils.uuid import uuid7


class AgentInterruptCommand(RequestDTO):
    """Represents a command for an agent interrupt."""

    name: str = Field(..., description='The name of the interrupt.')
    decision: Literal['approve', 'edit', 'reject'] = Field(
        ..., description='The decision for the action.'
    )
    edited_args: dict[str, Any] | None = Field(
        default=None, description='The edited arguments if the decision is "edit".'
    )
    reject_reason: str | None = Field(
        default=None, description='The reason for rejecting the action.'
    )


class AgentInput(RequestDTO):
    """Represents the input for an agent call."""

    query: str = Field(..., description='The input query for the agent.')
    commands: dict[str, AgentInterruptCommand] | None = Field(
        default=None,
        description='The interrupt commands for the agent. Keyed by the interrupt ID.',
    )


class AgentConfig(RequestDTO):
    """Represents the configuration for an agent call."""

    thread_id: UUID = Field(
        default_factory=uuid7, description='The thread ID for the agent.'
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description='The metadata for the agent call and any sub-calls.',
    )
    tags: list[str] = Field(
        default_factory=list,
        description='The tags for the agent call and any sub-calls.',
    )
    max_concurrency: int | None = Field(
        default=None, description='The maximum number of parallel calls to make.'
    )
    recursion_limit: int | None = Field(
        default=None, description='The maximum number of times a call can recurse.'
    )


class AgentRequest(AgentConfig):
    """Represents a request to an agent."""

    input: AgentInput = Field(..., description='The input for the agent.')


class AgentToolInterrupt(ResponseDTO):
    """Represents an interrupt for an agent tool."""

    id: str = Field(..., description='The ID of the interrupt.')
    name: str = Field(..., description='The name of the interrupt.')
    args: dict[str, Any] = Field(..., description='The arguments for the interrupt.')
    description: str = Field(..., description='The description of the interrupt.')
    allowed_decisions: list[str] = Field(
        ..., description='The decisions that are allowed for the interrupt.'
    )


class AgentResponse(ResponseDTO):
    """Represents the response from an agent."""

    message: AnyMessage = Field(..., description='The message returned by the agent.')
    interrupts: list[AgentToolInterrupt] = Field(
        default_factory=list, description='The interrupts for the agent.'
    )
    thread_id: UUID = Field(..., description='The thread ID for the agent.')


class AgentStateResponse(ResponseDTO):
    """Represents the state of an agent."""

    messages: list[BaseMessage] = Field(
        ..., description='The messages in the agent state.'
    )
    interrupts: list[AgentToolInterrupt] = Field(
        default_factory=list, description='The interrupts for the agent state.'
    )
