from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langchain_core.documents import Document
from langchain_tavily import TavilySearch
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

from agents.context import Context
from agents.soc_agent.agent import soc_agent
from agents.uefa_agent.agent import uefa_agent
from core.config import settings
from core.memory.extractor.base_memory_extractor import BaseMemoryExtractor
from core.memory.middleware import MemoryMiddleware
from core.memory.store.base_memory_store import BaseMemoryStore
from core.pii.handlers.base_handler import BasePIIHandler
from core.pii.middleware import PIIMiddleware
from core.prompt_manager import prompt_manager

Supervisor = CompiledStateGraph[Any, Context | None, Any, Any]


_supervisor_prompt = prompt_manager.get('supervisor_prompt')
_subagent_request_prompt = prompt_manager.get('subagent_request_prompt')


def _get_tavily_tool() -> TavilySearch:
    """Create and return the Tavily tool."""
    return TavilySearch(
        max_results=5,
        topic='general',
    )


def build_subagent_request_prompt(request: str, runtime: ToolRuntime[Context]) -> str:
    """Build a prompt for subagent requests.

    Subagent prompts must include a "query" placeholder that will be replaced
    with the original user message, and a "request" placeholder that will be
    replaced with the request or question for the subagent.

    Args:
        request: The request or question for the subagent.
        runtime: The runtime context of the tool, which includes the state
            of the conversation and other relevant information.

    Returns:
        A formatted prompt string for the subagent.
    """
    original_user_message = next(
        message for message in runtime.state['messages'] if message.type == 'human'
    )
    return _subagent_request_prompt.format(
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
        runtime: The runtime context of the tool, which includes the state
            of the conversation and other relevant information.
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
        runtime: The runtime context of the tool, which includes the state
            of the conversation and other relevant information.
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
        tools=[soc_agent_tool, uefa_agent_tool, _get_tavily_tool()],
        system_prompt=_supervisor_prompt.format(memory_context='Not found'),
        middleware=[
            PIIMiddleware(
                pii_handler=pii_handler,
            ),
            MemoryMiddleware(
                memory_store=memory_store,
                memory_extractor=memory_extractor,
                system_prompt=_supervisor_prompt,
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
