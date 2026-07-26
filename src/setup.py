from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Checkpointer
from sqlactive import DBConnection

from agents.supervisor import Supervisor, build_supervisor
from core.config import settings
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
from persistence.database import init_database
from persistence.repos.base_conversation_repository import BaseConversationRepository
from persistence.repos.conversation_repository import ConversationRepository


@dataclass(frozen=True)
class AppResources:
    """Dataclass to hold application resources for dependency injection."""

    db: DBConnection
    supervisor: Supervisor
    checkpointer: Checkpointer
    memory_store: BaseMemoryStore
    memory_extractor: BaseMemoryExtractor
    pii_handler: BasePIIHandler
    stream_transformer: BasePIIStreamTransformer
    conversation_repo: BaseConversationRepository


@asynccontextmanager
async def setup() -> AsyncGenerator[AppResources]:
    """Set up the application resources and yield them.

    This function initializes the database connection, checkpointer, memory store,
    memory extractor, PII handler, stream transformer, and conversation repository.
    It then yields an instance of AppResources containing all the initialized resources.

    It ensures that all resources are properly cleaned up after use. So, it is
    recommended to use this function to manage the lifecycle of application resources
    in an asynchronous context (e.g., a Starlette-based application).

    Usage:
        >>> async with setup() as app_resources:
            # Use app_resources here

        >>> ctx = setup()
        >>> app_resources = await ctx.__aenter__()
        >>> # Use app_resources here
        >>> await ctx.__aexit__(None, None, None)

    Yields:
        An instance of AppResources containing the initialized resources.
    """
    async with AsyncExitStack() as stack:
        db = await stack.enter_async_context(init_database())

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
        conversation_repo = ConversationRepository()

        async with build_supervisor(
            checkpointer=checkpointer,
            memory_store=memory_store,
            memory_extractor=memory_extractor,
            pii_handler=pii_handler,
        ) as supervisor:
            yield AppResources(
                db=db,
                supervisor=supervisor,
                checkpointer=checkpointer,
                memory_store=memory_store,
                memory_extractor=memory_extractor,
                pii_handler=pii_handler,
                stream_transformer=stream_transformer,
                conversation_repo=conversation_repo,
            )
