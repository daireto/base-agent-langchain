from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage


def join_messages(messages: list[BaseMessage]) -> str:
    """Join a list of messages into a single string.

    Args:
        messages: The list of messages to join.

    Returns:
        A single string containing all messages, formatted as "type: content".
    """
    return '\n'.join(f'{msg.type}: {msg.content}' for msg in messages)


def get_last_message_by_type[T: BaseMessage](
    message_type: type[T],
    messages: list[AnyMessage],
) -> tuple[T | None, int | None]:
    """Get the last user message from the list of messages."""
    last_msg = None
    last_msg_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], message_type):
            last_msg = messages[i]
            last_msg_idx = i
            break

    if last_msg is not None and last_msg_idx is not None:
        return last_msg, last_msg_idx  # type: ignore

    return None, None


def get_last_user_message(
    messages: list[AnyMessage],
) -> tuple[HumanMessage | None, int | None]:
    """Get the last user message from the list of messages."""
    return get_last_message_by_type(HumanMessage, messages)


def get_last_ai_message(
    messages: list[AnyMessage],
) -> tuple[AIMessage | None, int | None]:
    """Get the last AI message from the list of messages."""
    return get_last_message_by_type(AIMessage, messages)
