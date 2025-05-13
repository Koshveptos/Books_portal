import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для правильного импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импорты из core
from core.database import get_db
from core.exceptions import PermissionDeniedException
from core.logger_config import logger

# Импорты из FastAPI
from fastapi import Depends, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

# Импортируем User напрямую из файла для избежания циклической зависимости
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

# Секреты для JWT
ACCESS_TOKEN_SECRET = "your_access_token_secret"
REFRESH_TOKEN_SECRET = "your_refresh_token_secret"

# Настройка Bearer-транспорта
bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")


# Настройка JWT-стратегии
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=ACCESS_TOKEN_SECRET,
        lifetime_seconds=3600,
        token_audience=["fastapi-users:auth"],
    )


# Настройка AuthenticationBackend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# Настройка базы данных пользователей
async def get_user_db(session: AsyncSession = Depends(get_db)) -> SQLAlchemyUserDatabase:
    return SQLAlchemyUserDatabase(session, User)


# Кастомный UserManager
class UserManager(BaseUserManager[User, int]):
    # Реализация метода parse_id для обработки идентификаторов пользователей
    def parse_id(self, user_id: str) -> int:
        """
        Преобразует строковый ID пользователя в целочисленный.
        Этот метод необходим для работы JWT аутентификации.
        """
        try:
            return int(user_id)
        except ValueError:
            logger.error(f"Failed to parse user_id: {user_id}")
            raise ValueError(f"Invalid user ID format: {user_id}")

    async def create(self, user_create, **kwargs):
        user_dict = user_create.dict(exclude_unset=True)
        # Запрещаем регистрацию с is_moderator=True или is_superuser=True
        if user_dict.get("is_moderator", False) or user_dict.get("is_superuser", False):
            logger.warning(f"Attempt to register with elevated privileges: {user_dict.get('email')}")
            raise ValueError("Cannot register with elevated privileges")

        # Логируем параметры перед сохранением
        logger.info(f"User parameters before save: {user_dict}")

        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)

        logger.info(f"Creating new user: {user_dict.get('email')}")
        created_user = await self.user_db.create(user_dict)
        await self.on_after_register(created_user, None)
        logger.info(f"User created successfully: {created_user.email}")
        return created_user

    async def update(self, user_update, user, **kwargs):
        # Проверяем, что только суперпользователь может менять is_moderator или is_superuser
        if not user.is_superuser:
            user_dict = user_update.dict(exclude_unset=True)
            if "is_moderator" in user_dict or "is_superuser" in user_dict:
                logger.warning(f"User {user.email} (id: {user.id}) attempted to update privileged fields")
                raise ValueError("Only superusers can update privileged status fields")

        logger.info(f"Updating user: {user.email} (id: {user.id})")
        updated_user = await super().update(user_update, user, **kwargs)
        logger.info(f"User updated successfully: {updated_user.email}")
        return updated_user


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


# Инициализация FastAPIUsers
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# Получение текущего пользователя
current_active_user = fastapi_users.current_user(active=True)

# Получение суперпользователя
current_superuser = fastapi_users.current_user(active=True, superuser=True)


# Класс для проверки прав пользователя
class PermissionChecker:
    def __init__(self, require_superuser=False, require_moderator=False):
        self.require_superuser = require_superuser
        self.require_moderator = require_moderator

    async def __call__(self, user: User = Depends(current_active_user)):
        try:
            logger.debug(f"Checking permissions for user {user.email} (id: {user.id})")

            # Проверка на суперпользователя (если требуется)
            if self.require_superuser and not user.is_superuser:
                logger.warning(
                    f"Permission denied: User {user.email} (id: {user.id}) "
                    f"attempted to access superuser-only resource"
                )
                raise PermissionDeniedException(message="Для доступа требуются права администратора")

            # Проверка на модератора (если требуется и пользователь не суперпользователь)
            if self.require_moderator and not user.is_moderator and not user.is_superuser:
                logger.warning(
                    f"Permission denied: User {user.email} (id: {user.id}) "
                    f"attempted to access moderator-only resource"
                )
                raise PermissionDeniedException(message="Для доступа требуются права модератора или администратора")

            logger.debug(f"Permission check passed for user {user.email} (id: {user.id})")
            return user
        except Exception as e:
            if isinstance(e, PermissionDeniedException):
                raise
            logger.error(f"Unexpected error during permission check for user {user.email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при проверке прав доступа"
            )


# Зависимости для проверки прав
admin_only = PermissionChecker(require_superuser=True)
moderator_only = PermissionChecker(require_moderator=True)
admin_or_moderator = PermissionChecker(require_moderator=True)  # суперпользователи автоматически имеют доступ


# Функция для проверки прав администратора
async def check_admin(user: User = Depends(current_active_user)):
    """Проверяет, имеет ли пользователь права администратора"""
    try:
        if not user.is_superuser:
            logger.warning(
                f"Admin access denied: User {user.email} (id: {user.id}) " f"attempted to access admin-only resource"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права администратора")
        logger.debug(f"Admin access granted for user {user.email} (id: {user.id})")
        return user
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Unexpected error during admin check for user {user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при проверке прав администратора"
        )


# Экспортируемые объекты
__all__ = [
    "auth_backend",
    "fastapi_users",
    "current_active_user",
    "current_superuser",
    "admin_only",
    "moderator_only",
    "admin_or_moderator",
    "check_admin",
]
