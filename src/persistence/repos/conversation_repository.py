from datetime import UTC, datetime

from uuid_utils.compat import UUID

from core.definitions import DEFAULT_LIMIT
from core.enums import ConversationStatus, InterruptDecision
from core.errors import (
    ConversationNotFoundError,
    InterruptNameMismatchError,
    InterruptNotFoundError,
)
from dtos.agent import AgentInterruptCommand, AgentToolInterrupt
from persistence.models import Conversation, Interrupt, Message
from persistence.parsers.message_parsers import (
    LCMessage,
    langchain_message_to_message_model,
    message_model_to_langchain_message,
)
from persistence.repos.base_conversation_repository import BaseConversationRepository


class ConversationRepository(BaseConversationRepository):
    """Repository for managing conversations and messages."""

    async def create_conversation(
        self,
        user_id: str,
        thread_id: UUID,
        title: str | None = None,
        description: str | None = None,
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            thread_id=thread_id,
            title=title,
            description=description,
        )
        return await conversation.save()

    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[Conversation]:
        if limit <= 0:
            limit = DEFAULT_LIMIT

        query = (
            Conversation.where(Conversation.user_id == user_id)
            .order_by('-last_message_at')
            .limit(limit)
        )

        if skip > 0:
            query = query.offset(skip)

        conversations = await query.all()
        return list(conversations)

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        return await Conversation.get(conversation_id)

    async def get_conversation_by_thread_id(
        self, thread_id: UUID
    ) -> Conversation | None:
        return await Conversation.where(Conversation.thread_id == thread_id).one()

    async def update_conversation(
        self,
        conversation_id: UUID,
        title: str | None = None,
        description: str | None = None,
        status: ConversationStatus | None = None,
    ) -> Conversation:
        conversation = await Conversation.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)

        if title is not None:
            conversation.title = title
        if description is not None:
            conversation.description = description
        if status is not None:
            conversation.status = status
            if status == ConversationStatus.ACTIVE:
                conversation.archived_at = None
                conversation.deleted_at = None
            if status == ConversationStatus.ARCHIVED:
                conversation.archived_at = datetime.now(UTC)
            if status == ConversationStatus.DELETED:
                conversation.deleted_at = datetime.now(UTC)

        return await conversation.save()

    async def delete_conversation(self, conversation_id: UUID) -> None:
        if conversation := await Conversation.get(conversation_id):
            await conversation.delete()

    async def add_message_to_conversation(
        self,
        conversation_id: UUID,
        lc_message: LCMessage,
        interrupts: list[AgentToolInterrupt] | None = None,
    ) -> Message:
        conversation = await Conversation.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)

        message = langchain_message_to_message_model(lc_message)
        message.conversation_id = conversation_id

        if interrupts:
            message.interrupts = [
                Interrupt(
                    execution_id=interrupt.id,
                    name=interrupt.name,
                    args=interrupt.args,
                    description=interrupt.description,
                    allowed_decisions=interrupt.allowed_decisions,
                )
                for interrupt in interrupts
            ]

        await message.save()

        conversation.last_message_at = message.created_at
        await conversation.save()

        return message

    async def resume_interrupt(
        self,
        execution_id: str,
        command: AgentInterruptCommand,
        reviewer_id: str | None = None,
    ) -> Interrupt:
        interrupt = await Interrupt.where(Interrupt.execution_id == execution_id).one()
        if not interrupt:
            raise InterruptNotFoundError(execution_id)

        if interrupt.name != command.name:
            raise InterruptNameMismatchError(interrupt.name, command.name)

        interrupt.decision = InterruptDecision(command.decision)
        interrupt.edited_args = command.edited_args
        interrupt.reject_reason = command.reject_reason
        interrupt.reviewed_by = reviewer_id
        interrupt.reviewed_at = datetime.now(UTC)

        return await interrupt.save()

    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[Message]:
        conversation = await Conversation.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)

        if limit <= 0:
            limit = DEFAULT_LIMIT

        query = (
            Message.where(Message.conversation_id == conversation_id)
            .order_by('created_at')
            .limit(limit)
        )

        if skip > 0:
            query = query.offset(skip)

        messages = await query.all()
        return list(messages)

    async def get_lc_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[LCMessage]:
        messages = await self.get_messages(conversation_id, limit, skip)
        return [message_model_to_langchain_message(msg) for msg in messages]

    async def get_message(self, message_id: UUID) -> Message | None:
        return await Message.get(message_id)

    async def get_lc_message(self, message_id: UUID) -> LCMessage | None:
        message = await self.get_message(message_id)
        if not message:
            return None
        return message_model_to_langchain_message(message)
