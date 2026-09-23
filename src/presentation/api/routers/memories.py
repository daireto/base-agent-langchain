from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from core.definitions import DEFAULT_USER_ID
from presentation.api.dtos.memories import MemoriesResponse

if TYPE_CHECKING:
    from services.memory_service import MemoryService

router = APIRouter(
    prefix='/memories',
    tags=['memories'],
)


@router.get('/')
async def get_user_memories(
    request: Request, user_id: str = DEFAULT_USER_ID
) -> MemoriesResponse:
    """Get the memories associated with a specific user."""
    memory_service: MemoryService = request.app.state.memory_service
    memories = await memory_service.get_user_memories(user_id)
    return MemoriesResponse(memories=memories, user_id=user_id)
