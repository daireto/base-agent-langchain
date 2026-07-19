from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.chat_models import init_chat_model

from agents.soc_agent.tools import (
    abuseipdb_checker,
    add_ip_to_blacklist,
    get_all_blacklisted_ips,
    is_ip_blacklisted,
    remove_ip_from_blacklist,
    virustotal_analyzer,
)
from core.config import settings
from core.prompt_manager import prompt_manager

model = init_chat_model(
    model=settings.soc_agent.model,
    temperature=settings.soc_agent.temperature,
    max_tokens=settings.soc_agent.max_tokens,
    timeout=settings.soc_agent.timeout,
    max_retries=settings.soc_agent.max_retries,
    base_url=settings.soc_agent.base_url,
)

soc_agent = create_agent(
    model,
    tools=[
        abuseipdb_checker,
        add_ip_to_blacklist,
        get_all_blacklisted_ips,
        is_ip_blacklisted,
        remove_ip_from_blacklist,
        virustotal_analyzer,
    ],
    system_prompt=prompt_manager.get('soc_agent_prompt'),
    middleware=[
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
)
