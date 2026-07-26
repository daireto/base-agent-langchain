from uuid_utils.compat import UUID

from core.definitions import DEFAULT_LIMIT
from core.enums import ConversationStatus
from core.errors import ConversationNotFoundError, MessageNotFoundError
from persistence.models import Conversation, Message
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
        user_id: str,
        thread_id: UUID,
        title: str | None = None,
        description: str | None = None,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            user_id: The ID of the user creating the conversation.
            thread_id: The ID of the thread associated with the conversation.
            title: The title of the conversation. Defaults to None.
            description: The description of the conversation. Defaults to None.

        Returns:
            The newly created conversation.
        """
        return await self._conversation_repo.create_conversation(
            user_id=user_id,
            thread_id=thread_id,
            title=title,
            description=description,
        )

    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[Conversation]:
        """Return the conversations that belong to a user.

        Args:
            user_id: The ID of the user whose conversations will be retrieved.
            limit: The maximum number of conversations to return.
            skip: The number of conversations to skip before returning results.

        Returns:
            The list of conversations for the user.
        """
        return await self._conversation_repo.get_user_conversations(
            user_id=user_id,
            limit=limit,
            skip=skip,
        )

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """Return a conversation by its identifier.

        Args:
            conversation_id: The ID of the conversation to retrieve.

        Returns:
            The requested conversation.

        Raises:
            ConversationNotFoundError: If the conversation does not exist.
        """
        conversation = await self._conversation_repo.get_conversation(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def get_conversation_by_thread_id(self, thread_id: UUID) -> Conversation:
        """Return a conversation by its thread identifier.

        Args:
            thread_id: The thread ID associated with the conversation.

        Returns:
            The conversation linked to the thread.

        Raises:
            ConversationNotFoundError: If no conversation matches the thread ID.
        """
        conversation = await self._conversation_repo.get_conversation_by_thread_id(
            thread_id
        )
        if not conversation:
            raise ConversationNotFoundError(thread_id)
        return conversation

    async def update_conversation(
        self,
        conversation_id: UUID,
        title: str | None = None,
        description: str | None = None,
        status: ConversationStatus | None = None,
    ) -> Conversation:
        return await self._conversation_repo.update_conversation(
            conversation_id=conversation_id,
            title=title,
            description=description,
            status=status,
        )

    async def delete_conversation(self, conversation_id: UUID) -> None:
        """Delete a conversation by its identifier.

        Args:
            conversation_id: The ID of the conversation to delete.
        """
        return await self._conversation_repo.delete_conversation(conversation_id)

    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[Message]:
        """Return the messages for a conversation.

        Args:
            conversation_id: The ID of the conversation whose messages will be retrieved.
            limit: The maximum number of messages to return.
            skip: The number of messages to skip before returning results.

        Returns:
            The list of messages for the conversation.
        """
        return await self._conversation_repo.get_messages(
            conversation_id=conversation_id,
            limit=limit,
            skip=skip,
        )

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

    async def get_message(self, message_id: UUID) -> Message:
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
        return message

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
