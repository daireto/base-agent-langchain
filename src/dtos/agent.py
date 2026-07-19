from typing import Any, Literal

from langchain_core.messages import AnyMessage, BaseMessage
from pydantic import BaseModel, Field

from utils.uuid import str_uuid7


class AgentInterruptEditedAction(BaseModel):
    name: str = Field(..., description='The name of the edited action.')
    args: dict[str, Any] = Field(
        ..., description='The arguments for the edited action.'
    )


class AgentInterruptCommand(BaseModel):
    decision: Literal['approve', 'edit', 'reject'] = Field(
        ..., description='The decision for the interrupt command.'
    )
    edited_action: AgentInterruptEditedAction | None = Field(
        default=None, description='The edited action if the decision is "edit".'
    )
    reject_reason: str | None = Field(
        default=None, description='The reason for rejecting the interrupt command.'
    )


class AgentInput(BaseModel):
    query: str = Field(..., description='The input query for the agent.')
    commands: dict[str, AgentInterruptCommand] | None = Field(
        default=None, description='The interrupt commands for the agent.'
    )


class AgentConfig(BaseModel):
    thread_id: str = Field(
        default_factory=str_uuid7, description='The thread ID for the agent.'
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


class AgentToolInterrupt(BaseModel):
    name: str = Field(..., description='The name of the interrupt tool.')
    args: dict[str, Any] = Field(
        ..., description='The arguments for the interrupt tool.'
    )
    description: str = Field(..., description='The description of the interrupt tool.')
    allowed_decisions: list[str] = Field(
        ..., description='The decisions that are allowed for the interrupt tool.'
    )


class AgentRequest(AgentConfig):
    input: AgentInput = Field(..., description='The input for the agent.')


class AgentResponse(BaseModel):
    message: AnyMessage = Field(..., description='The message returned by the agent.')
    interrupts: list[AgentToolInterrupt] = Field(
        default_factory=list, description='The interrupts for the agent.'
    )


class AgentStateResponse(BaseModel):
    messages: list[BaseMessage] = Field(
        ..., description='The messages in the agent state.'
    )
    interrupts: list[AgentToolInterrupt] = Field(
        default_factory=list, description='The interrupts for the agent state.'
    )
