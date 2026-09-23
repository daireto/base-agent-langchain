from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from agents.uefa_agent.store import uefa_store
from core.config import settings
from presentation.api.a2a.routes import register_a2a_routes
from presentation.api.exception_handlers import exception_handlers
from presentation.api.logger import get_logger, setup_app_logger
from presentation.api.middlewares.access_log_middleware import AccessLogMiddleware
from presentation.api.middlewares.rate_limit_middleware import RateLimitMiddleware
from presentation.api.middlewares.security_headers_middleware import (
    SecurityHeadersMiddleware,
)
from presentation.api.routers.agent import router as agent_router
from presentation.api.routers.conversation import router as conversation_router
from presentation.api.routers.health import router as health_router
from presentation.api.routers.memories import router as memories_router
from presentation.api.routers.messages import router as messages_router
from services.agent_service import AgentService
from services.conversation_service import ConversationService
from services.memory_service import MemoryService
from setup import AppResources, setup


def register_routers(app: FastAPI) -> None:
    """Register routers in the FastAPI application.

    Args:
        app: The FastAPI application instance where routers will be registered.
    """
    app.include_router(agent_router)
    app.include_router(conversation_router)
    app.include_router(health_router)
    app.include_router(memories_router)
    app.include_router(messages_router)

    if settings.rest_server.a2a_enabled:
        register_a2a_routes(app)


def register_middlewares(app: FastAPI, include_rate_limit: bool = True) -> None:
    """Register middlewares in the FastAPI application.

    Args:
        app: The FastAPI application instance where middlewares will be registered.
        include_rate_limit: Whether to include the rate limit middleware.
            Defaults to True.
    """
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts=settings.rest_server.https,
        exclude_from_csp=['docs', 'redoc'],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.rest_cors.allow_origins.split(','),
        allow_methods=settings.rest_cors.allow_methods.split(','),
        allow_headers=settings.rest_cors.allow_headers.split(','),
        expose_headers=settings.rest_cors.expose_headers.split(','),
    )
    app.add_middleware(
        AccessLogMiddleware,
        logger=get_logger('access'),
        excluded_path_prefixes=settings.rest_log.access_log_excluded_path_prefixes,
    )
    app.add_middleware(CorrelationIdMiddleware)

    if settings.rest_server.https:
        app.add_middleware(HTTPSRedirectMiddleware)

    if include_rate_limit:
        app.add_middleware(
            RateLimitMiddleware,
            storage_uri=settings.rest_rate_limit.storage_uri.get_secret_value(),
            root_limit=settings.rest_rate_limit.root_limit,
        )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.rest_server.allowed_hosts.split(','),
    )


def register_services(app: FastAPI) -> None:
    """Register services in the FastAPI application state.

    Args:
        app: The FastAPI application instance where services will be registered.
    """
    app_resources: AppResources = app.state.app_resources

    app.state.agent_service = AgentService(
        supervisor=app_resources.supervisor,
        stream_transformer=app_resources.stream_transformer,
        conversation_repo=app_resources.conversation_repo,
    )
    app.state.conversation_service = ConversationService(
        conversation_repo=app_resources.conversation_repo,
    )
    app.state.memory_service = MemoryService(
        memory_store=app_resources.memory_store,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    app.state.logger.info('Starting app')

    async with setup() as app_resources:
        app.state.app_resources = app_resources
        register_services(app)

        app.state.logger.info(settings.rest_server.startup_msg)

        yield

        uefa_store.close()

        app.state.logger.info('Stopping app')

    app.state.logger.info('App stopped')


def create_app(
    logs_filepath: str | None = None,
) -> FastAPI:
    """Create the FastAPI application.

    Setups the application with routers and logger.
    Middlewares are not registered here.

    Args:
        logs_filepath: Filepath for log rotation.

    Returns:
        A FastAPI application instance.
    """
    app = FastAPI(
        debug=settings.rest_server.debug,
        exception_handlers=exception_handlers,
        lifespan=lifespan,
    )

    setup_app_logger(
        app=app,
        filepath=logs_filepath,
    )
    register_routers(app)

    return app


def create_default_app() -> FastAPI:
    """Calls create_app() and register the middlewares."""
    app = create_app(
        logs_filepath=settings.rest_log.path
        if not settings.rest_server.is_dev
        else None,
    )

    register_middlewares(app)

    return app
