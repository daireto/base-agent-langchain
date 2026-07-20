from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from core.enums import MessageRole, ToolStatus
from persistence.models import Message

LCMessage = AIMessage | HumanMessage | ToolMessage
"""LangChain message type alias for AIMessage, HumanMessage, and ToolMessage."""


def langchain_message_to_message_model(lc_message: LCMessage) -> Message:
    """Convert a LangChain message to a Message model.

    Args:
        lc_message: The LangChain message to convert.

    Returns:
        The corresponding Message model.
    """
    tool_calls = None
    invalid_tool_calls = None
    usage_metadata = None
    tool_call_id = None
    tool_status = None

    if isinstance(lc_message, AIMessage):
        tool_calls = lc_message.tool_calls
        invalid_tool_calls = lc_message.invalid_tool_calls
        usage_metadata = lc_message.usage_metadata
    elif isinstance(lc_message, ToolMessage):
        tool_call_id = lc_message.tool_call_id
        tool_status = ToolStatus(lc_message.status)

    return Message(
        role=MessageRole(lc_message.type),
        content=lc_message.content,
        name=lc_message.name,
        additional_kwargs=lc_message.additional_kwargs,
        response_metadata=lc_message.response_metadata,
        tool_calls=tool_calls,
        invalid_tool_calls=invalid_tool_calls,
        usage_metadata=usage_metadata,
        tool_call_id=tool_call_id,
        tool_status=tool_status,
    )


def message_model_to_langchain_message(message_model: Message) -> LCMessage:
    """Convert a Message model to a LangChain message.

    Args:
        message_model: The Message model to convert.

    Returns:
        The corresponding LangChain message.

    Raises:
        ValueError: If the message role is unknown.
    """
    if message_model.role == MessageRole.AI:
        return AIMessage(
            content=message_model.content,
            name=message_model.name,
            additional_kwargs=message_model.additional_kwargs or {},
            response_metadata=message_model.response_metadata or {},
            tool_calls=message_model.tool_calls or [],
            invalid_tool_calls=message_model.invalid_tool_calls or [],
            usage_metadata=message_model.usage_metadata,
        )

    if message_model.role == MessageRole.HUMAN:
        return HumanMessage(
            content=message_model.content,
            name=message_model.name,
            additional_kwargs=message_model.additional_kwargs or {},
            response_metadata=message_model.response_metadata or {},
        )

    if message_model.role == MessageRole.TOOL:
        return ToolMessage(
            content=message_model.content,
            name=message_model.name,
            additional_kwargs=message_model.additional_kwargs or {},
            response_metadata=message_model.response_metadata or {},
            tool_call_id=message_model.tool_call_id or '',
            status=message_model.tool_status or ToolStatus.SUCCESS,
        )

    raise ValueError(f'Unknown message role: {message_model.role}')
