from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, dynamic_prompt
from langchain.agents.middleware.types import ContextT, ModelRequest
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

from agents.context import Context
from agents.supervisor.tools import get_tavily_tool, soc_agent_tool, uefa_agent_tool
from core.config import settings
from core.memory.extractor.base_memory_extractor import BaseMemoryExtractor
from core.memory.middleware import MemoryMiddleware
from core.memory.store.base_memory_store import BaseMemoryStore
from core.pii.handlers.base_handler import BasePIIHandler
from core.pii.middleware import PIIMiddleware
from core.prompt.manager import prompt_manager

Supervisor = CompiledStateGraph[Any, Context | None, Any, Any]


@dynamic_prompt
def supervisor_prompt(_: ModelRequest[ContextT]) -> str:
    return prompt_manager.get('supervisor_prompt', memory_context='null')


@asynccontextmanager
async def build_supervisor(
    checkpointer: Checkpointer,
    memory_store: BaseMemoryStore,
    memory_extractor: BaseMemoryExtractor,
    pii_handler: BasePIIHandler,
) -> AsyncGenerator[Supervisor]:
    """Build and yield a supervisor agent with the specified tools and middleware.

    Args:
        checkpointer: The checkpointer to use for the supervisor agent.
        memory_store: The memory store to use for the supervisor agent.
        memory_extractor: The memory extractor to use for the supervisor agent.
        pii_handler: The PII handler to use for the supervisor agent.

    Yields:
        A supervisor agent with the specified tools and middleware.
    """
    supervisor_model = settings.supervisor.init_chat_model()
    summarization_model = settings.summarization.init_chat_model()

    supervisor = create_agent(
        supervisor_model,
        tools=[soc_agent_tool, uefa_agent_tool, get_tavily_tool()],
        middleware=[
            supervisor_prompt,
            PIIMiddleware(
                pii_handler=pii_handler,
            ),
            MemoryMiddleware(
                memory_store=memory_store,
                memory_extractor=memory_extractor,
            ),
            SummarizationMiddleware(
                model=summarization_model,
                trigger=('messages', 10),
                keep=('messages', 3),
            ),
        ],
        checkpointer=checkpointer,
        context_schema=Context,
        name='supervisor',
    )

    yield supervisor
