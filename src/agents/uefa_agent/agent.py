from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt
from langchain.agents.middleware.types import ContextT, ModelRequest
from langgraph.graph.state import CompiledStateGraph

from agents.uefa_agent.tools import uefa_docs_retriever
from core.config import settings
from core.prompt.manager import prompt_manager


@dynamic_prompt
def uefa_agent_prompt(_: ModelRequest[ContextT]) -> str:
    return prompt_manager.get('uefa_agent_prompt')


def get_uefa_agent() -> CompiledStateGraph:
    """Create and return the UEFA agent."""
    model = settings.uefa_agent.init_chat_model()

    return create_agent(
        model,
        tools=[uefa_docs_retriever],
        middleware=[uefa_agent_prompt],
        name='uefa_agent',
    )


uefa_agent = get_uefa_agent()
