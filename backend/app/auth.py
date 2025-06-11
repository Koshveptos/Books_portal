import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для правильного импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импорты из FastAPI
from fastapi import Depends, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

# Импортируем User напрямую из файла для избежания циклической зависимости
from models.user import User
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты из core
from app.core.database import get_db
from app.core.exceptions import PermissionDeniedException
from app.core.logger_config import logger

# Импортируем схемы пользователя
from app.schemas.user import UserCreate

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


# Класс менеджера пользователей
class UserManager(BaseUserManager[User, int]):
    reset_password_token_secret = ACCESS_TOKEN_SECRET
    verification_token_secret = ACCESS_TOKEN_SECRET

    async def on_after_register(self, user: User, request=None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(self, user: User, token: str, request=None):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(self, user: User, token: str, request=None):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

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

    async def create(self, user_create: UserCreate, safe: bool = False, **kwargs) -> User:
        try:
            logger.info("Starting user creation process")
            user_dict = user_create.model_dump()
            logger.info(f"User data after dict conversion: {user_dict}")

            # Проверяем наличие пароля
            if "password" not in user_dict:
                logger.error("Password field is missing in user data")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пароль обязателен для регистрации")

            # Проверяем права доступа только если safe=True
            if safe and (user_dict.get("is_superuser") or user_dict.get("is_moderator")):
                logger.warning(f"Attempt to register with elevated privileges: {user_dict.get('email')}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Невозможно создать пользователя с повышенными привилегиями",
                )

            logger.info(f"User parameters before save: {user_dict}")
            user_dict["hashed_password"] = self.password_helper.hash(user_dict.pop("password"))
            logger.info("Password hashed successfully")

            logger.info(f"Creating new user: {user_dict['email']}")
            try:
                created_user = await self.user_db.create(user_dict)
                logger.info(f"User created successfully in database: {created_user.email}")
                print(f"User {created_user.id} has registered.")
                logger.info(f"User registration completed: {created_user.email}")
                return created_user
            except IntegrityError as e:
                if "users_email_key" in str(e) or "ix_users_email" in str(e):
                    logger.warning(f"Attempt to register with existing email: {user_dict['email']}")
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT, detail="Пользователь с таким email уже существует"
                    )
                logger.error(f"Database integrity error during user creation: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Ошибка целостности данных при создании пользователя",
                )
            except Exception as e:
                logger.error(f"Unexpected error during user creation: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании пользователя"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error during user creation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании пользователя"
            )

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
current_active_user = fastapi_users.current_user(active=True, optional=False)
current_required_user = fastapi_users.current_user(active=True)

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
