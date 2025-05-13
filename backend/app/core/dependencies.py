from typing import AsyncGenerator

from auth import current_active_user
from core.config import settings
from core.database import AsyncSessionLocal
from core.logger_config import logger
from fastapi import Depends, HTTPException, status
from models.user import User
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

# Переиспользуем функцию current_active_user из auth модуля
get_current_active_user = current_active_user

# Создание объекта Redis-клиента или None, если не удалось подключиться
try:
    redis_connection = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=False,
        socket_timeout=5,
    )
    # Проверка соединения
    redis_connection.ping()
    logger.info("Redis client initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize Redis client: {str(e)}")
    redis_connection = None


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


async def get_redis_client() -> Redis:
    """
    Зависимость для получения Redis-клиента.
    Возвращает глобальный Redis-клиент или None, если подключение невозможно.
    """
    return redis_connection


async def check_moderator_permission(user: User = Depends(current_active_user)):
    """
    Проверяет, имеет ли пользователь права модератора.

    Аргументы:
        user: Текущий авторизованный пользователь

    Возвращает:
        True, если проверка пройдена успешно

    Вызывает:
        HTTPException: Если пользователь не имеет прав модератора
    """
    logger.debug(f"Checking moderator permission for user {user.email} (id: {user.id})")

    if not user.is_moderator:
        logger.warning(
            f"Permission denied: User {user.email} (id: {user.id}) " f"attempted to access moderator resource"
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Для доступа требуются права модератора")

    logger.debug(f"Moderator permission granted for user {user.email} (id: {user.id})")
    return True


async def check_admin_permission(user: User = Depends(current_active_user)):
    """
    Проверяет, имеет ли пользователь права администратора.

    Аргументы:
        user: Текущий авторизованный пользователь

    Возвращает:
        True, если проверка пройдена успешно

    Вызывает:
        HTTPException: Если пользователь не имеет прав администратора
    """
    logger.debug(f"Checking admin permission for user {user.email} (id: {user.id})")

    if not user.is_superuser:
        logger.warning(f"Permission denied: User {user.email} (id: {user.id}) " f"attempted to access admin resource")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Для доступа требуются права администратора")

    logger.debug(f"Admin permission granted for user {user.email} (id: {user.id})")
    return True


async def check_moderator_or_admin_permission(user: User = Depends(current_active_user)):
    """
    Проверяет, имеет ли пользователь права модератора или администратора.

    Аргументы:
        user: Текущий авторизованный пользователь

    Возвращает:
        True, если проверка пройдена успешно

    Вызывает:
        HTTPException: Если пользователь не имеет прав модератора или администратора
    """
    logger.debug(f"Checking moderator or admin permission for user {user.email} (id: {user.id})")

    if not user.is_moderator and not user.is_superuser:
        logger.warning(
            f"Permission denied: User {user.email} (id: {user.id}) " f"attempted to access moderator/admin resource"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Для доступа требуются права модератора или администратора"
        )

    logger.debug(f"Moderator or admin permission granted for user {user.email} (id: {user.id})")
    return True
