from dataclasses import dataclass
from enum import StrEnum

from uuid_utils.compat import UUID


@dataclass
class Error(Exception):
    """Base class for all exceptions in the application."""

    status: int
    title: str
    detail: str
    code: str
    type: str = 'about:blank'
    extra: dict[str, object] | None = None

    def __post_init__(self) -> None:
        super().__init__(self.detail)


class ErrorCode(StrEnum):
    CONVERSATION_NOT_FOUND = 'CONVERSATION_NOT_FOUND'
    INTERRUPT_NAME_MISMATCH = 'INTERRUPT_NAME_MISMATCH'
    INTERRUPT_NOT_FOUND = 'INTERRUPT_NOT_FOUND'
    INVALID_COMMAND_DECISION = 'INVALID_COMMAND_DECISION'
    MESSAGE_NOT_FOUND = 'MESSAGE_NOT_FOUND'
    MISSING_INTERRUPT_COMMAND = 'MISSING_INTERRUPT_COMMAND'
    REQUIRED_EDITED_ARGS = 'REQUIRED_EDITED_ARGS'
    UNEXPECTED_ERROR = 'UNEXPECTED_ERROR'
    VALIDATION_ERROR = 'VALIDATION_ERROR'


class ConversationNotFoundError(Error):
    """Raised when a conversation is not found."""

    def __init__(self, conversation_id: str | UUID, is_thread_id: bool = False) -> None:
        if is_thread_id:
            super().__init__(
                status=404,
                title='Conversation Not Found',
                detail=f'Conversation with thread ID {conversation_id} not found.',
                code=ErrorCode.CONVERSATION_NOT_FOUND,
                extra={'thread_id': str(conversation_id)},
            )
        else:
            super().__init__(
                status=404,
                title='Conversation Not Found',
                detail=f'Conversation with ID {conversation_id} not found.',
                code=ErrorCode.CONVERSATION_NOT_FOUND,
                extra={'conversation_id': str(conversation_id)},
            )


class InterruptNameMismatchError(Error):
    """Raised when an interrupt name does not match the expected name."""

    def __init__(self, expected_name: str, actual_name: str) -> None:
        super().__init__(
            status=400,
            title='Interrupt Name Mismatch',
            detail=f'Expected interrupt name "{expected_name}", but got "{actual_name}".',
            code=ErrorCode.INTERRUPT_NAME_MISMATCH,
            extra={'expected_name': expected_name, 'actual_name': actual_name},
        )


class InterruptNotFoundError(Error):
    """Raised when an interrupt is not found."""

    def __init__(self, execution_id: str) -> None:
        super().__init__(
            status=404,
            title='Interrupt Not Found',
            detail=f'Interrupt with execution ID {execution_id} not found.',
            code=ErrorCode.INTERRUPT_NOT_FOUND,
            extra={'execution_id': execution_id},
        )


class InvalidCommandDecisionError(Error):
    """Raised when a command decision is invalid."""

    def __init__(self, decision: str, interrupt_name: str) -> None:
        super().__init__(
            status=400,
            title='Invalid Command Decision',
            detail=f'Invalid decision "{decision}" for interrupt "{interrupt_name}".',
            code=ErrorCode.INVALID_COMMAND_DECISION,
            extra={'decision': decision, 'interrupt_name': interrupt_name},
        )


class MessageNotFoundError(Error):
    """Raised when a message is not found."""

    def __init__(self, message_id: str | UUID) -> None:
        super().__init__(
            status=404,
            title='Message Not Found',
            detail=f'Message with ID {message_id} not found.',
            code=ErrorCode.MESSAGE_NOT_FOUND,
            extra={'message_id': str(message_id)},
        )


class MissingInterruptCommandError(Error):
    """Raised when an interrupt command is missing in the input."""

    def __init__(self, interrupts: list[str]) -> None:
        joined = ', '.join(interrupts)
        super().__init__(
            status=409,
            title='Missing Interrupt Command',
            detail=f'The interrupt command is missing for the interrupts: {joined}.',
            code=ErrorCode.MISSING_INTERRUPT_COMMAND,
            extra={'interrupts': interrupts},
        )


class RequiredEditedArgsError(Error):
    """Raised when edited_args is required but not provided."""

    def __init__(self, interrupt_name: str) -> None:
        super().__init__(
            status=400,
            title='Edited Args Required',
            detail=f'Edited args are required for the interrupt "{interrupt_name}".',
            code=ErrorCode.REQUIRED_EDITED_ARGS,
            extra={'interrupt_name': interrupt_name},
        )
