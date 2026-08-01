from typing import Literal, overload

from uuid_utils.compat import UUID

from core.definitions import DEFAULT_LIMIT
from core.errors import ConversationNotFoundError, MessageNotFoundError
from dtos.conversation import (
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    UpdateConversationRequest,
)
from persistence.parsers.message_parsers import LCMessage
from persistence.repos.base_conversation_repository import BaseConversationRepository


class ConversationService:
    """Service for managing conversations and messages.

    Attributes:
        _conversation_repo: The repository for managing conversations.
    """

    def __init__(self, conversation_repo: BaseConversationRepository) -> None:
        """Initialize the service.

        Args:
            conversation_repo: The repository for managing conversations.
        """
        self._conversation_repo = conversation_repo

    async def create_conversation(
        self,
        request: CreateConversationRequest,
    ) -> ConversationResponse:
        """Create a new conversation.

        Args:
            request: The DTO containing the details for the new conversation.

        Returns:
            The DTO containing the details of the created conversation.
        """
        conversation = await self._conversation_repo.create_conversation(
            user_id=request.user_id,
            thread_id=request.thread_id,
            title=request.title,
            description=request.description,
        )
        return ConversationResponse.model_validate(conversation)

    @overload
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: Literal[False] = False,
    ) -> list[ConversationResponse]: ...

    @overload
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: Literal[True] = True,
    ) -> tuple[list[ConversationResponse], int]: ...

    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: bool = False,
    ) -> list[ConversationResponse] | tuple[list[ConversationResponse], int]:
        """Return the conversations that belong to a user.

        Args:
            user_id: The ID of the user whose conversations will be retrieved.
            limit: The maximum number of conversations to return.
            skip: The number of conversations to skip before returning results.
            with_count: Whether to return the total count of conversations
                along with the list.

        Returns:
            The list of conversations for the user, and optionally the total count.
        """
        result = await self._conversation_repo.get_user_conversations(
            user_id=user_id,
            limit=limit,
            skip=skip,
            with_count=with_count,
        )

        if isinstance(result, tuple):
            conversations, count = result
            return [
                ConversationResponse.model_validate(c) for c in conversations
            ], count

        return [ConversationResponse.model_validate(c) for c in result]

    async def get_conversation(self, conversation_id: UUID) -> ConversationResponse:
        """Return a conversation by its identifier.

        Args:
            conversation_id: The ID of the conversation to retrieve.

        Returns:
            The DTO containing the details of the conversation.

        Raises:
            ConversationNotFoundError: If the conversation does not exist.
        """
        conversation = await self._conversation_repo.get_conversation(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)
        return ConversationResponse.model_validate(conversation)

    async def get_conversation_by_thread_id(
        self, thread_id: UUID
    ) -> ConversationResponse:
        """Return a conversation by its thread identifier.

        Args:
            thread_id: The thread ID associated with the conversation.

        Returns:
            The DTO containing the details of the conversation.

        Raises:
            ConversationNotFoundError: If no conversation matches the thread ID.
        """
        conversation = await self._conversation_repo.get_conversation_by_thread_id(
            thread_id
        )
        if not conversation:
            raise ConversationNotFoundError(thread_id)
        return ConversationResponse.model_validate(conversation)

    async def update_conversation(
        self,
        conversation_id: UUID,
        request: UpdateConversationRequest,
    ) -> ConversationResponse:
        set_fields = request.model_dump(exclude_unset=True)
        conversation = await self._conversation_repo.update_conversation(
            conversation_id=conversation_id,
            title=set_fields.get('title'),
            description=set_fields.get('description'),
            status=set_fields.get('status'),
        )
        return ConversationResponse.model_validate(conversation)

    async def delete_conversation(self, conversation_id: UUID) -> None:
        """Delete a conversation by its identifier.

        Args:
            conversation_id: The ID of the conversation to delete.
        """
        return await self._conversation_repo.delete_conversation(conversation_id)

    @overload
    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: Literal[False] = False,
    ) -> list[MessageResponse]: ...

    @overload
    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: Literal[True] = True,
    ) -> tuple[list[MessageResponse], int]: ...

    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: bool = False,
    ) -> list[MessageResponse] | tuple[list[MessageResponse], int]:
        """Return the messages for a conversation.

        Args:
            conversation_id: The ID of the conversation whose messages will be retrieved.
            limit: The maximum number of messages to return.
            skip: The number of messages to skip before returning results.
            with_count: Whether to return the total count of messages along
                with the list.

        Returns:
            The list of messages for the conversation, and optionally the total count.
        """
        result = await self._conversation_repo.get_messages(
            conversation_id=conversation_id,
            limit=limit,
            skip=skip,
            with_count=with_count,
        )

        if isinstance(result, tuple):
            msgs, count = result
            return [MessageResponse.model_validate(msg) for msg in msgs], count

        return [MessageResponse.model_validate(msg) for msg in result]

    async def get_message(self, message_id: UUID) -> MessageResponse:
        """Return a message by its identifier.

        Args:
            message_id: The ID of the message to retrieve.

        Returns:
            The requested message.

        Raises:
            MessageNotFoundError: If the message does not exist.
        """
        message = await self._conversation_repo.get_message(message_id)
        if not message:
            raise MessageNotFoundError(message_id)
        return MessageResponse.model_validate(message)

    async def get_lc_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[LCMessage]:
        """Return the LangChain messages for a conversation.

        Args:
            conversation_id: The ID of the conversation whose messages will be retrieved.
            limit: The maximum number of messages to return.
            skip: The number of messages to skip before returning results.

        Returns:
            The list of LangChain messages for the conversation.
        """
        return await self._conversation_repo.get_lc_messages(
            conversation_id=conversation_id,
            limit=limit,
            skip=skip,
        )

    async def get_lc_message(self, message_id: UUID) -> LCMessage:
        """Return a LangChain message by its identifier.

        Args:
            message_id: The ID of the message to retrieve.

        Returns:
            The requested LangChain message.

        Raises:
            MessageNotFoundError: If the message does not exist.
        """
        lc_message = await self._conversation_repo.get_lc_message(message_id)
        if not lc_message:
            raise MessageNotFoundError(message_id)
        return lc_message
