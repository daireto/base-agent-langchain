from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import Any

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

from agents.supervisor import build_supervisor
from core.config import settings
from core.context import Context
from core.definitions import CHECKPOINTER_PATH
from core.memory.extractor.base_memory_extractor import BaseMemoryExtractor
from core.memory.extractor.llm_memory_extractor import LLMMemoryExtractor
from core.memory.store.base_memory_store import BaseMemoryStore
from core.memory.store.chroma_memory_store import ChromaMemoryStore
from core.pii.handlers.base_handler import BasePIIHandler
from core.pii.handlers.presidio_pii_handler import PresidioPIIHandler
from core.pii.stream_transformers.base_stream_transformer import (
    BasePIIStreamTransformer,
)
from core.pii.stream_transformers.pii_stream_transformer import PIIStreamTransformer
from core.pii.vault import MemoryVault
from core.prompt_manager import prompt_manager


@dataclass(frozen=True)
class Resources:
    checkpointer: Checkpointer
    memory_store: BaseMemoryStore
    memory_extractor: BaseMemoryExtractor
    pii_handler: BasePIIHandler
    stream_transformer: BasePIIStreamTransformer


@asynccontextmanager
async def setup() -> AsyncIterator[
    tuple[CompiledStateGraph[Any, Context | None, Any, Any], Resources]
]:
    async with AsyncExitStack() as stack:
        checkpointer_conn = await stack.enter_async_context(
            aiosqlite.connect(CHECKPOINTER_PATH)
        )

        checkpointer = AsyncSqliteSaver(checkpointer_conn)

        memory_store = ChromaMemoryStore()
        memory_extractor = LLMMemoryExtractor(
            settings.memory_extractor,
            system_prompt=prompt_manager.get('memory_extractor_prompt'),
        )

        pii_handler = PresidioPIIHandler(
            vault=MemoryVault(),
        )
        stream_transformer = PIIStreamTransformer(
            pii_handler=pii_handler,
        )

        resources = Resources(
            checkpointer=checkpointer,
            memory_store=memory_store,
            memory_extractor=memory_extractor,
            pii_handler=pii_handler,
            stream_transformer=stream_transformer,
        )

        async with build_supervisor(
            checkpointer=checkpointer,
            memory_store=memory_store,
            memory_extractor=memory_extractor,
            pii_handler=pii_handler,
        ) as supervisor:
            yield supervisor, resources
