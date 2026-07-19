from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.chat_models import init_chat_model
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langchain_core.documents import Document
from langchain_tavily import TavilySearch
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

from agents.soc_agent.agent import soc_agent
from agents.uefa_agent.agent import uefa_agent
from core.config import settings
from core.context import Context
from core.memory.extractor.base_memory_extractor import BaseMemoryExtractor
from core.memory.middleware import MemoryMiddleware
from core.memory.store.base_memory_store import BaseMemoryStore
from core.pii.handlers.base_handler import BasePIIHandler
from core.pii.middleware import PIIMiddleware
from core.prompt_manager import prompt_manager

supervisor_model = init_chat_model(
    model=settings.supervisor.model,
    temperature=settings.supervisor.temperature,
    max_tokens=settings.supervisor.max_tokens,
    timeout=settings.supervisor.timeout,
    max_retries=settings.supervisor.max_retries,
    base_url=settings.supervisor.base_url,
)

summarization_model = init_chat_model(
    model=settings.summarization.model,
    temperature=settings.summarization.temperature,
    max_tokens=settings.summarization.max_tokens,
    timeout=settings.summarization.timeout,
    max_retries=settings.summarization.max_retries,
    base_url=settings.summarization.base_url,
)

tavily_tool = TavilySearch(
    max_results=5,
    topic='general',
)

supervisor_prompt = prompt_manager.get('supervisor_prompt')
subagent_request_prompt = prompt_manager.get('subagent_request_prompt')


def build_subagent_request_prompt(request: str, runtime: ToolRuntime[Context]) -> str:
    original_user_message = next(
        message for message in runtime.state['messages'] if message.type == 'human'
    )
    return subagent_request_prompt.format(
        query=original_user_message.text,
        request=request,
    )


@tool
async def soc_agent_tool(request: str, runtime: ToolRuntime[Context]) -> str:
    """Handle requests and questions related to SOC operations.

    SOC operations:
    - Analyzing security alerts
    - Investigating incidents
    - Checking IP reputations
    - Blacklisting ip addresses
    - Querying the blacklist.

    Args:
        request: Request or question related to SOC operations.
    """
    prompt = build_subagent_request_prompt(request, runtime)
    result = await soc_agent.ainvoke(
        {'messages': [{'role': 'user', 'content': prompt}]}
    )
    return result['messages'][-1].text


@tool(response_format='content_and_artifact')
async def uefa_agent_tool(
    request: str, runtime: ToolRuntime[Context]
) -> tuple[str, list[Document]]:
    """Answer questions related to UEFA regulations.

    UEFa knowledge base has information about regulations of the following tournaments:
    - UEFA Champions League
    - UEFA Europa League
    - UEFA Conference League

    Args:
        request: Question related to UEFA operations.
    """
    prompt = build_subagent_request_prompt(request, runtime)
    result = await uefa_agent.ainvoke(
        {'messages': [{'role': 'user', 'content': prompt}]}
    )

    docs = []
    for msg in reversed(result['messages']):
        if isinstance(msg, ToolMessage) and msg.artifact:
            docs.extend(msg.artifact)
            break

    return result['messages'][-1].text, docs


@asynccontextmanager
async def build_supervisor(
    checkpointer: Checkpointer,
    memory_store: BaseMemoryStore,
    memory_extractor: BaseMemoryExtractor,
    pii_handler: BasePIIHandler,
) -> AsyncIterator[CompiledStateGraph[Any, Context | None, Any, Any]]:
    supervisor = create_agent(
        supervisor_model,
        tools=[soc_agent_tool, uefa_agent_tool, tavily_tool],
        system_prompt=supervisor_prompt.format(memory_context='Not found'),
        middleware=[
            PIIMiddleware(
                pii_handler=pii_handler,
            ),
            MemoryMiddleware(
                memory_store=memory_store,
                memory_extractor=memory_extractor,
                system_prompt=supervisor_prompt,
            ),
            SummarizationMiddleware(
                model=summarization_model,
                trigger=('messages', 10),
                keep=('messages', 3),
            ),
        ],
        checkpointer=checkpointer,
        context_schema=Context,
    )

    yield supervisor
