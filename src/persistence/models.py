from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from langchain_core.messages import (  # noqa: TC002
    InvalidToolCall,
    ToolCall,
    UsageMetadata,
)
from sqlactive import ActiveRecordBaseModel
from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, desc
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import UUID

from core.enums import ConversationStatus, InterruptDecision, MessageRole, ToolStatus
from persistence.types import GUID
from utils.uuid import uuid7


class BaseModel(ActiveRecordBaseModel):
    __abstract__ = True

    type_annotation_map = {
        UUID: GUID,
    }


class Conversation(BaseModel):
    __tablename__ = 'conversations'

    __table_args__ = (
        Index(
            'ix_conversation_user_last_message',
            'user_id',
            desc('last_message_at'),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    user_id: Mapped[str] = mapped_column(String(255), index=True)

    thread_id: Mapped[UUID] = mapped_column(unique=True, index=True)

    title: Mapped[str | None] = mapped_column(String(60))

    description: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[ConversationStatus] = mapped_column(
        SqlEnum(ConversationStatus),
        default=ConversationStatus.ACTIVE,
    )

    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list[Message]] = relationship(
        back_populates='conversation',
        cascade='all, delete-orphan',
    )


class Message(BaseModel):
    __tablename__ = 'messages'

    __table_args__ = (
        Index(
            'ix_message_conversation_id_id',
            'conversation_id',
            'id',
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey('conversations.id', ondelete='CASCADE'),
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(
        SqlEnum(MessageRole),
        index=True,
    )

    content: Mapped[str] = mapped_column(Text)

    name: Mapped[str | None] = mapped_column(String(255))

    additional_kwargs: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    response_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    tool_calls: Mapped[list[ToolCall] | None] = mapped_column(JSON)

    invalid_tool_calls: Mapped[list[InvalidToolCall] | None] = mapped_column(JSON)

    usage_metadata: Mapped[UsageMetadata | None] = mapped_column(JSON)

    tool_call_id: Mapped[str | None] = mapped_column(String(255))

    tool_status: Mapped[ToolStatus | None] = mapped_column(SqlEnum(ToolStatus))

    conversation: Mapped[Conversation] = relationship(
        back_populates='messages',
    )

    interrupts: Mapped[list[Interrupt]] = relationship(
        back_populates='message',
        cascade='all, delete-orphan',
    )


class Interrupt(BaseModel):
    __tablename__ = 'interrupts'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    message_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'messages.id',
            ondelete='CASCADE',
        ),
        index=True,
    )

    execution_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    name: Mapped[str] = mapped_column(String(255))

    args: Mapped[dict[str, Any]] = mapped_column(JSON)

    description: Mapped[str] = mapped_column(String(255))

    allowed_decisions: Mapped[list[str]] = mapped_column(JSON)

    decision: Mapped[InterruptDecision | None] = mapped_column(
        SqlEnum(InterruptDecision)
    )

    edited_args: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    reject_reason: Mapped[str | None] = mapped_column(Text)

    reviewed_by: Mapped[str | None] = mapped_column(String(255))

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    message: Mapped[Message] = relationship(
        back_populates='interrupts',
    )
