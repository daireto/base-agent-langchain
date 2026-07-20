from abc import ABC, abstractmethod

from uuid_utils.compat import UUID

from core.definitions import DEFAULT_LIMIT
from core.enums import ConversationStatus
from dtos.agent import AgentInterruptCommand, AgentToolInterrupt
from persistence.models import Conversation, Interrupt, Message
from persistence.parsers.message_parsers import LCMessage


class BaseConversationRepository(ABC):
    """Base class for conversation repositories."""

    @abstractmethod
    async def create_conversation(
        self,
        user_id: UUID,
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

    @abstractmethod
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[Conversation]:
        """Get all conversations for a user.

        Args:
            user_id: The ID of the user.
            limit: The maximum number of conversations to return.
            skip: The number of conversations to skip.

        Returns:
            A list of Conversation objects for the user.
        """

    @abstractmethod
    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """Get a conversation by its ID.

        Args:
            conversation_id: The ID of the conversation.

        Returns:
            The Conversation object if found, else None.

        Raises:
            ConversationNotFoundError: If the conversation with the given ID
                does not exist.
        """

    @abstractmethod
    async def get_conversation_by_thread_id(self, thread_id: UUID) -> Conversation:
        """Get a conversation by its thread ID.

        Args:
            thread_id: The ID of the thread.

        Returns:
            The Conversation object if found, else None.

        Raises:
            ConversationNotFoundError: If the conversation with the given thread ID
                does not exist.
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
    async def add_message(
        self,
        conversation_id: UUID,
        lc_message: LCMessage,
        interrupt: AgentToolInterrupt | None = None,
    ) -> Message:
        """Add a message to a conversation.

        Args:
            conversation_id: The ID of the conversation.
            lc_message: The LangChain message to add.
            interrupt: Optional AgentToolInterrupt associated with the message.

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
        reviewer_id: UUID,
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

    @abstractmethod
    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[Message]:
        """Get all messages for a conversation.

        Args:
            conversation_id: The ID of the conversation.

        Returns:
            A list of Message objects for the conversation.

        Raises:
            ConversationNotFoundError: If the conversation does not exist.
        """

    @abstractmethod
    async def get_lc_messages(
        self,
        conversation_id: UUID,
        limit: int = DEFAULT_LIMIT,
        skip: int = 0,
    ) -> list[LCMessage]:
        """Get all LangChain messages for a conversation.

        Calls get_messages and converts the Message objects to LangChain messages.
        """

    @abstractmethod
    async def get_message(self, message_id: UUID) -> Message:
        """Get a message by its ID.

        Args:
            message_id: The ID of the message.

        Returns:
            The Message object if found, else None.

        Raises:
            MessageNotFoundError: If the message with the given ID does not exist.
        """

    @abstractmethod
    async def get_lc_message(self, message_id: UUID) -> LCMessage:
        """Get a LangChain message by its ID.

        Calls get_message and converts the Message object to a LangChain message.
        """
