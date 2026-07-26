from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlactive import DBConnection

from core.config import settings
from persistence.models import BaseModel


@asynccontextmanager
async def init_database() -> AsyncGenerator[DBConnection]:
    db = DBConnection(settings.database.url.get_secret_value())
    await db.init_db(BaseModel)
    yield db
    await db.close()
