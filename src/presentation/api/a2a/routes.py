from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from fastapi import FastAPI

from core.config import settings
from presentation.api.a2a.card import create_agent_card
from presentation.api.a2a.executor import A2AAgentExecutor


def register_a2a_routes(app: FastAPI) -> None:
    """Register A2A routes to the FastAPI application.

    Args:
        app: The FastAPI application instance where A2A routes will be registered.
    """
    agent_card = create_agent_card(
        name=settings.rest_server.a2a_card_name,
        description=settings.rest_server.a2a_card_description,
        version=settings.rest_server.a2a_card_version,
    )

    executor = A2AAgentExecutor()

    task_store = InMemoryTaskStore()

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        agent_card=agent_card,
    )

    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(
            request_handler,
            rpc_url='/a2a/jsonrpc',
        ),
        rest_routes=create_rest_routes(
            request_handler,
            path_prefix='/a2a/rest',
        ),
    )
