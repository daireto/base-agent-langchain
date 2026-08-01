from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from uuid_utils.compat import UUID

from core.definitions import DEFAULT_LIMIT
from dtos.common import Pagination
from dtos.conversation import MessageResponse
from utils.pagination import compute_skip, compute_total_pages

if TYPE_CHECKING:
    from services.conversation_service import ConversationService

router = APIRouter(
    prefix='/messages',
    tags=['messages'],
)


@router.get('/{conversation_id}')
async def get_messages(
    request: Request, conversation_id: UUID, page: int = 1, limit: int = DEFAULT_LIMIT
) -> Pagination[MessageResponse]:
    """Get the messages associated with a specific conversation."""
    service: ConversationService = request.app.state.conversation_service
    skip = compute_skip(page, limit)
    messages, count = await service.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        skip=skip,
        with_count=True,
    )
    total_pages = compute_total_pages(count, limit)
    return Pagination(
        items=messages,
        page=page,
        size=limit,
        total=count,
        total_pages=total_pages,
    )


@router.get('/{message_id}')
async def get_message(request: Request, message_id: UUID) -> MessageResponse:
    """Get a specific message by its ID."""
    service: ConversationService = request.app.state.conversation_service
    return await service.get_message(message_id)
