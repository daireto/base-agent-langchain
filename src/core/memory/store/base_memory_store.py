from abc import ABC, abstractmethod


class BaseMemoryStore(ABC):
    """Base class for memory stores."""

    @abstractmethod
    async def search(self, user_id: str, query: str, k: int = 5) -> list[str]:
        """Search for relevant memories based on a query.

        Args:
        user_id: The ID of the user to search memories for.
        query: The query to search for.
        k: The number of results to return. Defaults to 5.

        Returns:
            A list of formatted memory strings.
        """

    @abstractmethod
    async def save(self, user_id: str, memories: list[str]) -> None:
        """Save new memories for a user.

        Args:
            user_id: The ID of the user to save memories for.
            memories: A list of memories to save.
        """

    @abstractmethod
    async def get_user_memories(self, user_id: str, k: int = 5) -> list[str]:
        """Get all memories for a user.

        Args:
            user_id: The ID of the user to get memories for.
            k: The number of results to return, by default 5.

        Returns:
            A list of formatted memory strings.
        """
