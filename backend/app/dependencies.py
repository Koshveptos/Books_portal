from typing import AsyncGenerator

from core.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость для получения сессии базы данных.
    Создает новую сессию для каждого запроса и закрывает ее после завершения запроса.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
