from langchain_core.messages import AIMessageChunk, AnyMessage

from core.pii.handlers.base_handler import BasePIIHandler
from core.pii.stream_transformers.base_stream_transformer import (
    BasePIIStreamTransformer,
)

_DEFAULT_STREAM_LOOKBACK = 32


class PIIStreamTransformer(BasePIIStreamTransformer):
    """A stream transformer that handles PII anonymization and deanonymization.

    Attributes:
        _pii_handler: The PII handler used for anonymization and deanonymization.
        _buffers: A dictionary to hold buffered content for each thread.
        _lookback: The number of characters to keep in the buffer for each thread.
    """

    def __init__(
        self,
        pii_handler: BasePIIHandler,
        lookback: int = _DEFAULT_STREAM_LOOKBACK,
    ) -> None:
        """Initialize the PIIStreamTransformer.

        Args:
            pii_handler: The PII handler used for anonymization and deanonymization.
            lookback: The number of characters to keep in the buffer for each thread.
        """
        self._pii_handler = pii_handler
        self._buffers: dict[str, str] = {}
        self._lookback = lookback

    def transform_stream_chunk(
        self, message: AnyMessage, thread_id: str
    ) -> AnyMessage | None:
        if not isinstance(message.content, str) or not message.content:
            return message

        if not isinstance(message, AIMessageChunk):
            new_content = self._deanonymize(message.content, vault_key=thread_id)
            return message.model_copy(update={'content': new_content})

        held = self._buffers.get(thread_id, '')
        combined = held + message.content
        combined = self._deanonymize(combined, vault_key=thread_id)

        # Determine how much of the buffer to emit downstream
        emit_end = max(0, len(combined) - self._lookback)
        self._buffers[thread_id] = combined[emit_end:]
        emit = combined[:emit_end]

        if not emit:
            return None

        return message.model_copy(update={'content': emit})

    def flush_buffer(self, thread_id: str) -> AIMessageChunk | None:
        held = self._buffers.pop(thread_id, '')

        if not held:
            return None

        held = self._deanonymize(held, vault_key=thread_id)
        return AIMessageChunk(content=held)

    def drop_buffer(self, thread_id: str) -> None:
        self._buffers.pop(thread_id, None)

    def finalize(self) -> None:
        self._buffers.clear()

    def _deanonymize(self, content: str, vault_key: str) -> str:
        """De-anonymize the given content using the PII handler."""
        return self._pii_handler.deanonymize(content, vault_key=vault_key)
