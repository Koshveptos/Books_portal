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
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationException,
    PermissionDeniedException,
    UserAlreadyExistsException,
)
from app.core.logger_config import logger

# Импортируем схемы пользователя
from app.schemas.user import UserCreate

# Настройка Bearer-транспорта
bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")


# Настройка JWT-стратегии
def get_jwt_strategy() -> JWTStrategy:
    """Создает и возвращает JWT стратегию аутентификации"""
    try:
        if not settings.JWT_SECRET_KEY:
            logger.error("Отсутствует секретный ключ JWT")
            raise AuthenticationException("Ошибка конфигурации JWT")

        if not settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES:
            logger.error("Не задано время жизни токена")
            raise AuthenticationException("Ошибка конфигурации JWT")

        strategy = JWTStrategy(
            secret=settings.JWT_SECRET_KEY,
            lifetime_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            token_audience=["fastapi-users:auth"],
        )

        if not strategy:
            logger.error("Не удалось создать JWT стратегию")
            raise AuthenticationException("Ошибка создания JWT стратегии")

        return strategy
    except AuthenticationException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании JWT стратегии: {str(e)}")
        raise AuthenticationException("Ошибка настройки аутентификации")


# Настройка AuthenticationBackend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# Настройка базы данных пользователей
async def get_user_db(session: AsyncSession = Depends(get_db)) -> SQLAlchemyUserDatabase:
    """Создает и возвращает экземпляр базы данных пользователей"""
    try:
        if not session:
            logger.error("Сессия базы данных не инициализирована")
            raise AuthenticationException("Ошибка доступа к базе данных")

        user_db = SQLAlchemyUserDatabase(session, User)
        if not user_db:
            logger.error("Не удалось создать базу данных пользователей")
            raise AuthenticationException("Ошибка создания базы данных пользователей")

        return user_db
    except AuthenticationException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании базы данных пользователей: {str(e)}")
        raise AuthenticationException("Ошибка доступа к базе данных пользователей")


# Класс менеджера пользователей
class UserManager(BaseUserManager[User, int]):
    """Менеджер пользователей с расширенной функциональностью"""

    reset_password_token_secret = settings.JWT_SECRET_KEY
    verification_token_secret = settings.JWT_SECRET_KEY

    async def on_after_register(self, user: User, request=None):
        """Обработчик события после регистрации пользователя"""
        logger.info(f"Пользователь {user.id} успешно зарегистрирован")
        try:
            # Здесь можно добавить дополнительную логику после регистрации
            pass
        except Exception as e:
            logger.error(f"Ошибка в обработчике after_register: {str(e)}")

    async def on_after_forgot_password(self, user: User, token: str, request=None):
        """Обработчик события после запроса сброса пароля"""
        logger.info(f"Пользователь {user.id} запросил сброс пароля")
        try:
            # Здесь можно добавить отправку email с токеном
            pass
        except Exception as e:
            logger.error(f"Ошибка в обработчике after_forgot_password: {str(e)}")

    async def on_after_request_verify(self, user: User, token: str, request=None):
        """Обработчик события после запроса верификации"""
        logger.info(f"Запрошена верификация для пользователя {user.id}")
        try:
            # Здесь можно добавить отправку email с токеном верификации
            pass
        except Exception as e:
            logger.error(f"Ошибка в обработчике after_request_verify: {str(e)}")

    def parse_id(self, user_id: str) -> int:
        """
        Преобразует строковый ID пользователя в целочисленный.

        Args:
            user_id: Строковый ID пользователя

        Returns:
            int: Целочисленный ID пользователя

        Raises:
            ValueError: Если ID имеет неверный формат
        """
        try:
            return int(user_id)
        except ValueError:
            logger.error(f"Ошибка преобразования ID пользователя: {user_id}")
            raise ValueError(f"Неверный формат ID пользователя: {user_id}")

    async def create(self, user_create: UserCreate, safe: bool = False, **kwargs) -> User:
        """
        Создает нового пользователя.

        Args:
            user_create: Данные для создания пользователя
            safe: Флаг безопасного создания
            **kwargs: Дополнительные параметры

        Returns:
            User: Созданный пользователь

        Raises:
            HTTPException: При ошибках создания пользователя
        """
        try:
            logger.info("Начало процесса создания пользователя")
            user_dict = user_create.model_dump()

            # Проверка наличия пароля
            if "password" not in user_dict:
                logger.error("Отсутствует поле пароля в данных пользователя")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пароль обязателен для регистрации")

            # Проверка прав доступа
            if safe and (user_dict.get("is_superuser") or user_dict.get("is_moderator")):
                logger.warning(f"Попытка регистрации с повышенными привилегиями: {user_dict.get('email')}")
                raise PermissionDeniedException("Невозможно создать пользователя с повышенными привилегиями")

            # Хеширование пароля
            user_dict["hashed_password"] = self.password_helper.hash(user_dict.pop("password"))
            logger.info("Пароль успешно хеширован")

            # Создание пользователя
            try:
                created_user = await self.user_db.create(user_dict)
                logger.info(f"Пользователь успешно создан: {created_user.email}")
                return created_user
            except IntegrityError as e:
                if "users_email_key" in str(e) or "ix_users_email" in str(e):
                    logger.warning(f"Попытка регистрации с существующим email: {user_dict['email']}")
                    raise UserAlreadyExistsException()
                logger.error(f"Ошибка целостности данных при создании пользователя: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Ошибка целостности данных при создании пользователя",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Непредвиденная ошибка при создании пользователя: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при создании пользователя"
            )

    async def update(self, user_update, user: User, **kwargs) -> User:
        """
        Обновляет данные пользователя.

        Args:
            user_update: Данные для обновления
            user: Пользователь для обновления
            **kwargs: Дополнительные параметры

        Returns:
            User: Обновленный пользователь

        Raises:
            ValueError: При попытке обновления привилегированных полей
        """
        try:
            # Проверка прав на обновление привилегированных полей
            if not user.is_superuser:
                user_dict = user_update.dict(exclude_unset=True)
                if "is_moderator" in user_dict or "is_superuser" in user_dict:
                    logger.warning(f"Попытка обновления привилегированных полей пользователем {user.email}")
                    raise PermissionDeniedException("Только администраторы могут обновлять привилегированные поля")

            logger.info(f"Обновление пользователя: {user.email}")
            updated_user = await super().update(user_update, user, **kwargs)
            logger.info(f"Пользователь успешно обновлен: {updated_user.email}")
            return updated_user
        except Exception as e:
            logger.error(f"Ошибка при обновлении пользователя {user.email}: {str(e)}")
            raise


async def get_user_manager(user_db=Depends(get_user_db)) -> UserManager:
    """Создает и возвращает менеджер пользователей"""
    try:
        if not user_db:
            logger.error("База данных пользователей не инициализирована")
            raise AuthenticationException("Ошибка доступа к базе данных пользователей")

        manager = UserManager(user_db)
        if not manager:
            logger.error("Не удалось создать менеджер пользователей")
            raise AuthenticationException("Ошибка создания менеджера пользователей")

        yield manager
    except AuthenticationException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании менеджера пользователей: {str(e)}")
        raise AuthenticationException("Ошибка инициализации менеджера пользователей")


# Инициализация FastAPIUsers
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# Зависимости для получения текущего пользователя
current_active_user = fastapi_users.current_user(active=True, optional=False)
current_required_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)


class PermissionChecker:
    """Класс для проверки прав пользователя"""

    def __init__(self, require_superuser: bool = False, require_moderator: bool = False):
        self.require_superuser = require_superuser
        self.require_moderator = require_moderator

    async def __call__(self, user: User = Depends(current_active_user)) -> User:
        """
        Проверяет права пользователя.

        Args:
            user: Пользователь для проверки

        Returns:
            User: Пользователь, если проверка пройдена

        Raises:
            PermissionDeniedException: При недостаточных правах
        """
        try:
            logger.debug(f"Проверка прав для пользователя {user.email}")

            # Проверка на суперпользователя
            if self.require_superuser and not user.is_superuser:
                logger.warning(
                    f"Отказано в доступе: пользователь {user.email} попытался получить доступ к ресурсу администратора"
                )
                raise PermissionDeniedException("Для доступа требуются права администратора")

            # Проверка на модератора
            if self.require_moderator and not user.is_moderator and not user.is_superuser:
                logger.warning(
                    f"Отказано в доступе: пользователь {user.email} попытался получить доступ к ресурсу модератора"
                )
                raise PermissionDeniedException("Для доступа требуются права модератора или администратора")

            logger.debug(f"Проверка прав пройдена для пользователя {user.email}")
            return user
        except PermissionDeniedException:
            raise
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при проверке прав пользователя {user.email}: {str(e)}")
            raise PermissionDeniedException("Ошибка при проверке прав доступа")


# Зависимости для проверки прав
admin_only = PermissionChecker(require_superuser=True)
moderator_only = PermissionChecker(require_moderator=True)
admin_or_moderator = PermissionChecker(require_moderator=True)


async def check_admin(user: User = Depends(current_active_user)) -> User:
    """
    Проверяет права администратора.

    Args:
        user: Пользователь для проверки

    Returns:
        User: Пользователь, если он администратор

    Raises:
        PermissionDeniedException: Если пользователь не администратор
    """
    try:
        if not user.is_superuser:
            logger.warning(f"Отказано в доступе администратора: пользователь {user.email}")
            raise PermissionDeniedException("Требуются права администратора")
        logger.debug(f"Доступ администратора предоставлен пользователю {user.email}")
        return user
    except PermissionDeniedException:
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при проверке прав администратора: {str(e)}")
        raise PermissionDeniedException("Ошибка при проверке прав администратора")


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
