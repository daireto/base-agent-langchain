from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, dynamic_prompt
from langchain.agents.middleware.types import ContextT, ModelRequest
from langgraph.graph.state import CompiledStateGraph

from agents.soc_agent.tools import (
    abuseipdb_checker,
    add_ip_to_blacklist,
    get_all_blacklisted_ips,
    is_ip_blacklisted,
    remove_ip_from_blacklist,
    virustotal_analyzer,
)
from core.config import settings
from core.prompt.manager import prompt_manager


@dynamic_prompt
def soc_agent_prompt(_: ModelRequest[ContextT]) -> str:
    return prompt_manager.get('soc_agent_prompt')


def get_soc_agent() -> CompiledStateGraph:
    """Create and return the SOC agent."""
    model = settings.soc_agent.init_chat_model()

    return create_agent(
        model,
        tools=[
            abuseipdb_checker,
            add_ip_to_blacklist,
            get_all_blacklisted_ips,
            is_ip_blacklisted,
            remove_ip_from_blacklist,
            virustotal_analyzer,
        ],
        middleware=[
            soc_agent_prompt,
            HumanInTheLoopMiddleware(
                interrupt_on={
                    'add_ip_to_blacklist': {
                        'allowed_decisions': ['approve', 'reject'],
                    },
                    'remove_ip_from_blacklist': {
                        'allowed_decisions': ['approve', 'reject'],
                    },
                },
                description_prefix='Modificación de la lista negra de IPs pendiente de revisión.',
            ),
        ],
        name='soc_agent',
    )


soc_agent = get_soc_agent()
