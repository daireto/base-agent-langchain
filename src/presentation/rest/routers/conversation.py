from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from uuid_utils.compat import UUID

from core.definitions import DEFAULT_LIMIT
from dtos.common import Pagination
from dtos.conversation import (
    ConversationResponse,
    CreateConversationRequest,
    UpdateConversationRequest,
)
from utils.pagination import compute_skip, compute_total_pages

if TYPE_CHECKING:
    from services.conversation_service import ConversationService

router = APIRouter(
    prefix='/conversations',
    tags=['conversations'],
)


@router.post('/')
async def create_conversation(
    request: Request, data: CreateConversationRequest
) -> ConversationResponse:
    """Create a new conversation."""
    service: ConversationService = request.app.state.conversation_service
    return await service.create_conversation(data)


@router.get('/user/{user_id}')
async def get_user_conversations(
    request: Request, user_id: str, page: int = 1, limit: int = DEFAULT_LIMIT
) -> Pagination[ConversationResponse]:
    """Get the conversations associated with a specific user."""
    service: ConversationService = request.app.state.conversation_service
    skip = compute_skip(page, limit)
    conversations, count = await service.get_user_conversations(
        user_id=user_id,
        limit=limit,
        skip=skip,
        with_count=True,
    )
    total_pages = compute_total_pages(count, limit)
    return Pagination(
        items=conversations,
        page=page,
        size=limit,
        total=count,
        total_pages=total_pages,
    )


@router.get('/thread/{thread_id}')
async def get_conversation_by_thread_id(
    request: Request, thread_id: UUID
) -> ConversationResponse:
    """Get a specific conversation by its thread ID."""
    service: ConversationService = request.app.state.conversation_service
    return await service.get_conversation_by_thread_id(thread_id)


@router.get('/{conversation_id}')
async def get_conversation(
    request: Request, conversation_id: UUID
) -> ConversationResponse:
    """Get a specific conversation by its ID."""
    service: ConversationService = request.app.state.conversation_service
    return await service.get_conversation(conversation_id)


@router.patch('/{conversation_id}')
async def update_conversation(
    request: Request, conversation_id: UUID, data: UpdateConversationRequest
) -> ConversationResponse:
    """Update a specific conversation by its ID."""
    service: ConversationService = request.app.state.conversation_service
    return await service.update_conversation(conversation_id, data)


@router.delete('/{conversation_id}', status_code=204)
async def delete_conversation(request: Request, conversation_id: UUID) -> None:
    """Delete a specific conversation by its ID."""
    service: ConversationService = request.app.state.conversation_service
    await service.delete_conversation(conversation_id)
