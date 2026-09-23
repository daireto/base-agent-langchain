from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill


def create_agent_card(
    *,
    name: str,
    description: str,
    version: str = '1.0.0',
) -> AgentCard:
    """Create an A2A agent card with the specified name, description, and version.

    Args:
        name: The name of the agent card.
        description: The description of the agent card.
        version: The version of the agent card. Defaults to '1.0.0'.

    Returns:
        The created agent card.
    """
    return AgentCard(
        name=name,
        description=description,
        version=version,
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
        ),
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
        supported_interfaces=[
            AgentInterface(
                protocol_binding='JSONRPC',
                url='http://localhost:8000/jsonrpc',
                protocol_version='1.0.0',
            ),
            AgentInterface(
                protocol_binding='HTTP+JSON',
                url='http://localhost:8000/api',
                protocol_version='1.0.0',
            ),
        ],
        skills=[
            AgentSkill(
                id='general',
                name='General Agent',
                description=description,
                tags=[
                    'general',
                    'assistant',
                ],
                examples=[
                    'Ayúdame a analizar esta información',
                    'Cómo funciona la clasificación en la UEFa Champions League?',
                    'Esta IP 192.168.1.1 es segura?',
                    '¿Qué es un agente de IA?',
                    'Analiza esta URL: https://www.example.com',
                ],
            ),
        ],
    )
