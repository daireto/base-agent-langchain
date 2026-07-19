from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from core.definitions import DEFAULT_USER_ID
from presentation.rest.dtos.memories import MemoriesResponse

if TYPE_CHECKING:
    from core.memory.store.base_memory_store import BaseMemoryStore

router = APIRouter(
    prefix='/memories',
    tags=['memories'],
)


@router.get('/')
async def get_user_memories(
    request: Request, user_id: str = DEFAULT_USER_ID
) -> MemoriesResponse:
    memory_store: BaseMemoryStore = request.app.state.resources.memory_store
    memories = await memory_store.get_user_memories(user_id)
    return MemoriesResponse(memories=memories, user_id=user_id)
