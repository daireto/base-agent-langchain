from collections.abc import AsyncIterable
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from dtos.agent import AgentConfig, AgentRequest, AgentResponse, AgentStateResponse

if TYPE_CHECKING:
    from services.agent_service import AgentService

_RETRY_MILLISECONDS = 5000

router = APIRouter(
    prefix='/agent',
    tags=['agent'],
)


@router.post('/invoke')
async def invoke(request: Request, agent_request: AgentRequest) -> AgentResponse:
    agent_service: AgentService = request.app.state.agent_service
    return await agent_service.invoke(agent_request)


@router.post('/stream', response_class=EventSourceResponse)
async def stream(
    request: Request, agent_request: AgentRequest
) -> AsyncIterable[ServerSentEvent]:
    agent_service: AgentService = request.app.state.agent_service
    async for sse_event in agent_service.stream(agent_request):
        yield ServerSentEvent(
            data=sse_event.data,
            event=sse_event.event,
            retry=_RETRY_MILLISECONDS,
        )


@router.get('/state/{thread_id:str}')
async def get_state(request: Request, thread_id: str) -> AgentStateResponse:
    agent_service: AgentService = request.app.state.agent_service
    state = await agent_service.get_state(AgentConfig(thread_id=thread_id))
    return agent_service.parse_state_to_response(state)
