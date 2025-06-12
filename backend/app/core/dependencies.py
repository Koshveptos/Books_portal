"""
Модуль с зависимостями FastAPI.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db_session
from app.core.logger_config import logger
from app.core.redis import get_redis_client as get_redis_connection
from app.core.redis import init_redis as init_redis_connection
from app.models.user import User

# Переиспользуем функцию current_active_user из auth модуля
get_current_active_user = current_active_user

# Глобальная переменная для хранения Redis клиента
redis_connection: Optional[Redis] = None


async def init_redis() -> None:
    """Инициализация Redis клиента"""
    global redis_connection
    try:
        await init_redis_connection()
        redis_connection = await get_redis_connection()
        logger.info("Redis client initialized successfully")
    except Exception as e:
        logger.error(
            "Failed to initialize Redis client", extra={"error": str(e), "error_type": type(e).__name__}, exc_info=True
        )
        # Не выбрасываем исключение, а просто логируем ошибку
        logger.warning("Application will continue without Redis")
        redis_connection = None


async def get_redis_client() -> Optional[Redis]:
    """
    Получение Redis клиента.

    Returns:
        Optional[Redis]: Redis клиент или None в случае ошибки
    """
    global redis_connection
    if not redis_connection:
        try:
            redis_connection = await get_redis_connection()
        except Exception as e:
            logger.error(
                "Failed to get Redis client", extra={"error": str(e), "error_type": type(e).__name__}, exc_info=True
            )
            return None
    return redis_connection


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость для получения сессии базы данных"""
    async with get_db_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error occurred")


async def check_moderator_permission(user: User = Depends(current_active_user)):
    """Проверка прав модератора"""
    if not user.is_moderator:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user


async def check_admin_permission(user: User = Depends(current_active_user)):
    """Проверка прав администратора"""
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user


async def check_moderator_or_admin_permission(user: User = Depends(current_active_user)):
    """Проверка прав модератора или администратора"""
    if not (user.is_moderator or user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user
