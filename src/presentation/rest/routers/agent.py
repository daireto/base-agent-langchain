from collections.abc import AsyncIterable
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from uuid_utils.compat import UUID

from dtos.agent import AgentRequest, AgentResponse, AgentStateResponse

if TYPE_CHECKING:
    from services.agent_service import AgentService

_RETRY_MILLISECONDS = 5000

router = APIRouter(
    prefix='/agent',
    tags=['agent'],
)


@router.post(
    '/invoke',
    summary='Invoke the agent with a request and get a response.',
)
async def invoke(request: Request, agent_request: AgentRequest) -> AgentResponse:
    """Invoke the agent with a request and wait for a response."""
    agent_service: AgentService = request.app.state.agent_service
    return await agent_service.invoke(agent_request)


@router.post(
    '/stream',
    response_class=EventSourceResponse,
    summary='Stream the agent response as Server-Sent Events (SSE).',
)
async def stream(
    request: Request, agent_request: AgentRequest
) -> AsyncIterable[ServerSentEvent]:
    """Stream the agent response as Server-Sent Events (SSE)."""
    agent_service: AgentService = request.app.state.agent_service
    async for sse_event in agent_service.stream(agent_request):
        yield ServerSentEvent(
            data=sse_event.data,
            event=sse_event.event,
            retry=_RETRY_MILLISECONDS,
        )


@router.get(
    '/state/{thread_id}',
    summary='Get the current state of the agent for a specific thread.',
)
async def get_state(request: Request, thread_id: UUID) -> AgentStateResponse:
    """Get the current state of the agent for a specific thread."""
    agent_service: AgentService = request.app.state.agent_service
    state = await agent_service.get_state(thread_id)
    return agent_service.parse_state_to_response(state)
