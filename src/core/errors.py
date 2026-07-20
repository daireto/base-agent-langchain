from dataclasses import dataclass
from enum import StrEnum


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
    MISSING_INTERRUPT_COMMAND = 'MISSING_INTERRUPT_COMMAND'
    UNEXPECTED_ERROR = 'UNEXPECTED_ERROR'
    VALIDATION_ERROR = 'VALIDATION_ERROR'


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
