from abc import ABC, abstractmethod

from langchain_core.messages import AnyMessage


class BasePIIStreamTransformer(ABC):
    @abstractmethod
    def transform_stream_chunk(
        self, message: AnyMessage, thread_id: str
    ) -> AnyMessage | None:
        """Anonymize the given content using the PII handler.

        Args:
            message: The message to be transformed.
            thread_id: The ID of the thread to which the chunk belongs.

        Returns:
            The transformed message with anonymized content,
            or None if no transformation is needed.
        """

    @abstractmethod
    def flush_buffer(self, thread_id: str) -> AnyMessage | None:
        """Flush the buffer for the given thread_id and return any remaining content.

        Args:
            thread_id: The ID of the thread to which the buffer belongs.

        Returns:
            The message containing the flushed content,
            or None if there is no remaining content.
        """

    @abstractmethod
    def drop_buffer(self, thread_id: str) -> None:
        """Drop the buffer for the given thread_id.

        Args:
            thread_id: The ID of the thread to which the buffer belongs.
        """

    @abstractmethod
    def finalize(self) -> None:
        """Perform any finalization steps.

        Used to perform tasks such as clearing buffers or releasing resources.
        """
