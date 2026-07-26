from core.memory.store.base_memory_store import BaseMemoryStore


class MemoryService:
    """Service for managing user memories.

    Attributes:
        _memory_store: The memory store used to retrieve user memories.
    """

    def __init__(self, memory_store: BaseMemoryStore) -> None:
        """Initialize the MemoryService.

        Args:
            memory_store: An instance of BaseMemoryStore to interact
                with the memory storage.
        """
        self._memory_store = memory_store

    async def get_user_memories(self, user_id: str) -> list[str]:
        """Get the list of memories for a specific user.

        Args:
            user_id: The ID of the user whose memories are to be retrieved.

        Returns:
            A list of memories associated with the user.
        """
        return await self._memory_store.get_user_memories(user_id)
