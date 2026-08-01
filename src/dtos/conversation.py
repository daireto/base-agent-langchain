from datetime import datetime
from typing import Any

from langchain_core.messages import InvalidToolCall, ToolCall, UsageMetadata
from pydantic import Field
from uuid_utils.compat import UUID

from core.enums import ConversationStatus, InterruptDecision, MessageRole, ToolStatus
from dtos.base import EntityResponseDTO, RequestDTO


class CreateConversationRequest(RequestDTO):
    """Request DTO for creating a new conversation."""

    user_id: str = Field(
        ..., description='The ID of the user creating the conversation'
    )
    thread_id: UUID = Field(
        ..., description='The ID of the thread to which the conversation belongs'
    )
    title: str | None = Field(default=None, description='The title of the conversation')
    description: str | None = Field(
        default=None, description='The description of the conversation'
    )


class UpdateConversationRequest(RequestDTO):
    """Request DTO for updating an existing conversation."""

    title: str | None = Field(
        default=None, description='The new title of the conversation'
    )
    description: str | None = Field(
        default=None, description='The new description of the conversation'
    )
    status: ConversationStatus | None = Field(
        default=None, description='The new status of the conversation'
    )


class ConversationResponse(EntityResponseDTO):
    """Response DTO for a conversation."""

    user_id: str = Field(
        ..., description='The ID of the user who owns the conversation'
    )
    thread_id: UUID = Field(
        ..., description='The ID of the thread to which the conversation belongs'
    )
    title: str | None = Field(default=None, description='The title of the conversation')
    description: str | None = Field(
        default=None, description='The description of the conversation'
    )
    status: ConversationStatus = Field(
        ..., description='The status of the conversation'
    )
    last_message_at: datetime | None = Field(
        default=None,
        description='The timestamp of the last message in the conversation',
    )
    archived_at: datetime | None = Field(
        default=None, description='The timestamp when the conversation was archived'
    )
    deleted_at: datetime | None = Field(
        default=None, description='The timestamp when the conversation was deleted'
    )


class InterruptResponse(EntityResponseDTO):
    """Response DTO for a message interrupt."""

    message_id: UUID = Field(
        ..., description='The ID of the message that was interrupted'
    )
    execution_id: str = Field(..., description='The execution ID of the interrupt')
    name: str = Field(..., description='The name of the interrupt')
    args: dict[str, Any] = Field(..., description='The arguments for the interrupt')
    description: str = Field(..., description='The description of the interrupt')
    allowed_decisions: list[str] = Field(
        ..., description='The list of allowed decisions'
    )
    decision: InterruptDecision = Field(
        ..., description='The decision made for the interrupt'
    )
    edited_args: dict[str, Any] | None = Field(
        default=None, description='The edited arguments for the interrupt'
    )
    reject_reason: str | None = Field(
        default=None, description='The reason for rejecting the interrupt'
    )
    reviewed_by: str | None = Field(
        default=None, description='The user who reviewed the interrupt'
    )
    reviewed_at: datetime | None = Field(
        default=None, description='The timestamp when the interrupt was reviewed'
    )


class MessageResponse(EntityResponseDTO):
    """Response DTO for a conversation message."""

    conversation_id: UUID = Field(
        ..., description='The ID of the conversation to which the message belongs'
    )
    role: MessageRole = Field(
        ..., description='The role of the message sender (e.g., user, assistant)'
    )
    content: str = Field(..., description='The content of the message')
    name: str | None = Field(default=None, description='The name of the message sender')
    additional_kwargs: dict[str, Any] | None = Field(
        default=None, description='Additional keyword arguments for the message'
    )
    response_metadata: dict[str, Any] | None = Field(
        default=None, description='Metadata about the message response'
    )
    tool_calls: list[ToolCall] | None = Field(
        default=None, description='The tool calls made in the message'
    )
    invalid_tool_calls: list[InvalidToolCall] | None = Field(
        default=None, description='The invalid tool calls made in the message'
    )
    usage_metadata: UsageMetadata | None = Field(
        default=None, description='Metadata about the usage of the message'
    )
    tool_call_id: str | None = Field(
        default=None, description='The ID of the tool call'
    )
    tool_status: ToolStatus | None = Field(
        default=None, description='The status of the tool call'
    )
    interrupts: list[InterruptResponse] | None = Field(
        default=None, description='The list of interrupts associated with the message'
    )
