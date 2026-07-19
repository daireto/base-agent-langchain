from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from agents.uefa_agent.tools import uefa_docs_retriever
from core.config import settings
from core.prompt_manager import prompt_manager

model = init_chat_model(
    model=settings.uefa_agent.model,
    temperature=settings.uefa_agent.temperature,
    max_tokens=settings.uefa_agent.max_tokens,
    timeout=settings.uefa_agent.timeout,
    max_retries=settings.uefa_agent.max_retries,
    base_url=settings.uefa_agent.base_url,
)

uefa_agent = create_agent(
    model,
    tools=[uefa_docs_retriever],
    system_prompt=prompt_manager.get('uefa_agent_prompt'),
)
