"""
Настройки аутентификации и авторизации.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройка транспорта для JWT (Bearer token для заголовка Authorization)
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


# Настройка стратегии JWT
def get_jwt_strategy() -> JWTStrategy:
    """
    Получение стратегии JWT.
    """
    # Отладочное логирование
    logger.info(f"Initializing JWT strategy with secret key length: {len(settings.SECRET_KEY)}")
    logger.info(f"Token lifetime: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")

    strategy = JWTStrategy(
        secret=settings.SECRET_KEY,
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        algorithm="HS256",  # Явно указываем алгоритм
        token_audience=["fastapi-users:auth"],  # Явно указываем аудиторию
    )

    # Мы переопределяем метод read_token для добавления детального логирования
    original_read_token = strategy.read_token

    async def read_token_with_logging(token: str, *args, **kwargs):
        logger.info(f"Reading JWT token: {token[:15]}...")
        try:
            result = await original_read_token(token, *args, **kwargs)
            logger.info(f"Token decoded successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Error decoding token: {str(e)}")
            raise

    # Заменяем оригинальный метод на наш с логированием
    strategy.read_token = read_token_with_logging

    return strategy


# Настройка бэкенда аутентификации
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# Функция для получения базы данных пользователей
async def get_user_db(session: AsyncSession = Depends(get_db)):
    """
    Получение базы данных пользователей.
    """
    yield SQLAlchemyUserDatabase(session, User)


# Класс менеджера пользователей
class UserManager(UUIDIDMixin, BaseUserManager[User, int]):
    """
    Менеджер пользователей.
    """

    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """
        Вызывается после регистрации пользователя.
        """
        logger.info(f"User {user.id} has registered.")
        # Автоматически делаем нового пользователя модератором для тестирования
   
        user_dict = {"is_moderator": True}
        await self.user_db.update(user, user_dict)

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        """
        Вызывается после запроса сброса пароля.
        """
        logger.info(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None):
        """
        Вызывается после запроса верификации.
        """
        logger.info(f"Verification requested for user {user.id}. Verification token: {token}")


# Функция для получения менеджера пользователей
async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """
    Получение менеджера пользователей.
    """
    yield UserManager(user_db)


# Настройка FastAPI Users
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# Получение текущего пользователя с обязательной авторизацией
current_required_user = fastapi_users.current_user(active=True)


# Функция для проверки модератора
async def current_moderator(user: User = Depends(current_required_user)):
    """
    Получение текущего пользователя с правами модератора.

    Требуется Bearer JWT токен авторизации.
    Функция проверит, есть ли у пользователя права модератора.

    Raises:
        HTTPException: 401 если пользователь не авторизован
                      403 если пользователь не имеет прав модератора
    """
    # проверка на авторизацию уже выполнена в current_required_user
    if not user.is_moderator:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для выполнения операции")
    return user
