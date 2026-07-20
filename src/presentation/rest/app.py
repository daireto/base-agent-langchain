from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from agents.uefa_agent.store import close_qdrant_client
from core.config import settings
from presentation.rest.exception_handlers import exception_handlers
from presentation.rest.logger import get_logger, setup_app_logger
from presentation.rest.middlewares.access_log_middleware import AccessLogMiddleware
from presentation.rest.middlewares.rate_limit_middleware import RateLimitMiddleware
from presentation.rest.middlewares.security_headers_middleware import (
    SecurityHeadersMiddleware,
)
from presentation.rest.routers.agent import router as agent_router
from presentation.rest.routers.health import router as health_router
from presentation.rest.routers.memories import router as memories_router
from services.agent_service import AgentService
from setup import Resources, setup

if TYPE_CHECKING:
    from agents.supervisor import Supervisor


def register_routers(app: FastAPI) -> None:
    app.include_router(agent_router)
    app.include_router(health_router)
    app.include_router(memories_router)


def register_middlewares(app: FastAPI, include_rate_limit: bool = True) -> None:
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts=settings.rest_server.https,
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
    supervisor: Supervisor = app.state.supervisor
    resources: Resources = app.state.resources

    app.state.agent_service = AgentService(
        supervisor=supervisor,
        stream_transformer=resources.stream_transformer,
        conversation_repo=resources.conversation_repo,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.logger.info('Starting app')

    async with setup() as (supervisor, resources):
        app.state.supervisor = supervisor
        app.state.resources = resources
        register_services(app)

        app.state.logger.info(settings.rest_server.startup_msg)

        yield

        close_qdrant_client()

        app.state.logger.info('Stopping app')

    app.state.logger.info('App stopped')


def create_app(
    logs_filepath: str | None = None,
) -> FastAPI:
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
    app = create_app(
        logs_filepath=settings.rest_log.path
        if not settings.rest_server.is_dev
        else None,
    )

    register_middlewares(app)

    return app
