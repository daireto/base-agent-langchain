from fastapi import APIRouter

from presentation.rest.dtos.health import ServerHealthResponse
from presentation.rest.health import server_health

router = APIRouter(
    prefix='/health',
    tags=['health'],
)


@router.get('/')
def read_health() -> ServerHealthResponse:
    return ServerHealthResponse(
        message='ok'
        if server_health.is_healthy
        else server_health.get_unhealthy_reason(),
        healthy=server_health.is_healthy,
    )
