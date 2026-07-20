from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlactive import DBConnection

from core.config import settings
from persistence.models import BaseModel

db = DBConnection(settings.database.url.get_secret_value())


@asynccontextmanager
async def get_db_connection() -> AsyncIterator[DBConnection]:
    await db.init_db(BaseModel)
    yield db
    await db.close()
