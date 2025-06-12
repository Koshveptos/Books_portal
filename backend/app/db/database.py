from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logger_config import log_db_error

# Создаем асинхронный движок
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
)

# Создаем фабрику сессий
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """Получение сессии базы данных"""
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            log_db_error(e, {"operation": "get_db", "error_type": type(e).__name__, "error_details": str(e)})
            # raise DatabaseException("Ошибка при работе с базой данных")
