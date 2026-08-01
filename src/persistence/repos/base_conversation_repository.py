from abc import ABC, abstractmethod
from typing import Literal, overload

from uuid_utils.compat import UUID

from core.definitions import DEFAULT_LIMIT
from core.enums import ConversationStatus
from dtos.agent import AgentInterruptCommand, AgentToolInterrupt
from persistence.models import Conversation, Interrupt, Message
from persistence.parsers.message_parsers import (
    LCMessage,
    message_model_to_langchain_message,
)


class BaseConversationRepository(ABC):
    """Base class for conversation repositories."""

    @abstractmethod
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
            thread_id: The ID of the thread to which the conversation belongs.
            title: The title of the conversation.
            description: The description of the conversation.

        Returns:
            The created Conversation object.
        """

    @overload
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: Literal[False] = False,
    ) -> list[Conversation]: ...

    @overload
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: Literal[True] = True,
    ) -> tuple[list[Conversation], int]: ...

    @abstractmethod
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: bool = False,
    ) -> list[Conversation] | tuple[list[Conversation], int]:
        """Get all conversations for a user.

        Args:
            user_id: The ID of the user.
            limit: The maximum number of conversations to return.
            skip: The number of conversations to skip.
            with_count: Whether to return the total count of conversations
                along with the list.

        Returns:
            A list of Conversation objects for the user, or a tuple containing
            the list of Conversation objects and the total count of conversations
            if with_count is True.
        """

    @abstractmethod
    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        """Get a conversation by its ID.

        Args:
            conversation_id: The ID of the conversation.

        Returns:
            The Conversation object if found, else None.
        """

    @abstractmethod
    async def get_conversation_by_thread_id(
        self, thread_id: UUID
    ) -> Conversation | None:
        """Get a conversation by its thread ID.

        Args:
            thread_id: The ID of the thread.

        Returns:
            The Conversation object if found, else None.
        """

    @abstractmethod
    async def update_conversation(
        self,
        conversation_id: UUID,
        title: str | None = None,
        description: str | None = None,
        status: ConversationStatus | None = None,
    ) -> Conversation:
        """Update a conversation's title and/or description.

        Args:
            conversation_id: The ID of the conversation.
            title: The new title of the conversation.
            description: The new description of the conversation.
            status: The new status of the conversation.

        Returns:
            The updated Conversation object.

        Raises:
            ConversationNotFoundError: If the conversation with the given ID
                does not exist.
        """

    @abstractmethod
    async def delete_conversation(self, conversation_id: UUID) -> None:
        """Delete a conversation by its ID.

        Args:
            conversation_id: The ID of the conversation.
        """

    @abstractmethod
    async def add_message_to_conversation(
        self,
        conversation_id: UUID,
        lc_message: LCMessage,
        interrupts: list[AgentToolInterrupt] | None = None,
    ) -> Message:
        """Add a message to a conversation.

        Args:
            conversation_id: The ID of the conversation.
            lc_message: The LangChain message to add.
            interrupts: Optional list of AgentToolInterrupts associated
                with the message.

        Returns:
            The created Message object.

        Raises:
            ConversationNotFoundError: If the conversation does not exist.
        """

    @abstractmethod
    async def resume_interrupt(
        self,
        execution_id: str,
        command: AgentInterruptCommand,
        reviewer_id: str | None = None,
    ) -> Interrupt:
        """Resume an interrupt by its execution ID.

        Args:
            execution_id: The execution ID of the interrupt.
            command: The command to resume the interrupt.
            reviewer_id: The ID of the user reviewing the interrupt.

        Returns:
            The updated Interrupt object.

        Raises:
            InterruptNotFoundError: If the interrupt with the given execution ID
                does not exist.
            InterruptNameMismatchError: If the interrupt name does not match
                the expected name.
        """

    @overload
    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: Literal[False] = False,
    ) -> list[Message]: ...

    @overload
    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: Literal[True] = True,
    ) -> tuple[list[Message], int]: ...

    @abstractmethod
    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
        with_count: bool = False,
    ) -> list[Message] | tuple[list[Message], int]:
        """Get all messages for a conversation.

        Args:
            conversation_id: The ID of the conversation.
            limit: The maximum number of messages to return.
            skip: The number of messages to skip.
            with_count: Whether to return the total count of messages
                along with the list.

        Returns:
            A list of Message objects for the conversation, or a tuple containing
            the list of Message objects and the total count of messages
            if with_count is True.

        Raises:
            ConversationNotFoundError: If the conversation does not exist.
        """

    @abstractmethod
    async def get_message(self, message_id: UUID) -> Message | None:
        """Get a message by its ID.

        Args:
            message_id: The ID of the message.

        Returns:
            The Message object if found, else None.
        """

    async def get_lc_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[LCMessage]:
        """Get all LangChain messages for a conversation.

        Calls get_messages and converts the Message objects to LangChain messages.
        """
        messages = await self.get_messages(
            conversation_id, limit, skip, with_count=False
        )
        return [message_model_to_langchain_message(msg) for msg in messages]

    async def get_lc_message(self, message_id: UUID) -> LCMessage | None:
        """Get a LangChain message by its ID.

        Calls get_message and converts the Message object to a LangChain message.
        """
        message = await self.get_message(message_id)
        if not message:
            return None
        return message_model_to_langchain_message(message)
