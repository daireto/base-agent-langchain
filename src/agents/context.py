from pydantic import BaseModel


class Context(BaseModel):
    """Conversation context schema for the supervisor agent."""

    user_id: str
    """Unique identifier for the user associated with the conversation."""
