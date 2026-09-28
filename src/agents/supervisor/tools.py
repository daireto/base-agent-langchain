from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langchain_core.documents import Document
from langchain_tavily import TavilySearch

from agents.context import Context
from agents.soc_agent.agent import soc_agent
from agents.uefa_agent.agent import uefa_agent
from core.prompt.manager import prompt_manager


def get_tavily_tool() -> TavilySearch:
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
    return prompt_manager.get(
        'subagent_request_prompt',
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
