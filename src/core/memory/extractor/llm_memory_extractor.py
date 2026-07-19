from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from core.config import ModelSettings
from core.memory.extractor.base_memory_extractor import BaseMemoryExtractor
from utils.messages import join_messages


class LLMMemoryExtractor(BaseMemoryExtractor):
    """Memory extractor that uses a language model to extract
    relevant information from a conversation.
    """

    def __init__(self, config: ModelSettings, system_prompt: str) -> None:
        """Initialize a LLMMemoryExtractor.

        Args:
            config: The configuration for the language model used in memory extraction.
            system_prompt: The system prompt to use for guiding
                the memory extraction process.
        """
        self.__llm = init_chat_model(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            max_retries=config.max_retries,
            base_url=config.base_url,
        )
        self._system_prompt = system_prompt

    async def extract(self, messages: list[BaseMessage]) -> list[str]:
        conversation = join_messages(messages)

        response = await self.__llm.ainvoke(
            [
                SystemMessage(content=self._system_prompt),
                HumanMessage(content=conversation),
            ]
        )

        if not isinstance(response.content, str):
            response.content = str(response.content)

        if 'not found' in response.content.lower().strip():
            return []

        memories = response.content.split('\n')
        return [memory.strip() for memory in memories if memory.strip()]
