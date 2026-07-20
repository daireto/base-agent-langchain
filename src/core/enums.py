from enum import StrEnum


class ConversationStatus(StrEnum):
    ACTIVE = 'active'
    ARCHIVED = 'archived'
    DELETED = 'deleted'


class InterruptDecision(StrEnum):
    APPROVE = 'approve'
    REJECT = 'reject'
    EDIT = 'edit'


class MessageRole(StrEnum):
    AI = 'ai'
    HUMAN = 'human'
    TOOL = 'tool'


class ToolStatus(StrEnum):
    SUCCESS = 'success'
    ERROR = 'error'
