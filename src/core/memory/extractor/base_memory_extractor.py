from abc import ABC, abstractmethod

from langchain_core.messages import AnyMessage


class BaseMemoryExtractor(ABC):
    """Base class for memory extractors."""

    @abstractmethod
    async def extract(self, messages: list[AnyMessage]) -> list[str]:
        """Extract relevant information from a list of messages.

        Args:
            messages: The list of messages from which to extract information.

        Returns:
            A list of strings containing the extracted information.

        Examples:
            >>> extractor = SomeMemoryExtractor()
            >>> messages = [HumanMessage(content="My name is John."), HumanMessage(content="I like programming.")]
            >>> memories = await extractor.extract(messages)
            >>> memories
            ['User is named John', 'Likes programming']
        """
