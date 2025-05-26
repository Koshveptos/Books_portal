import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

# Добавляем корневую директорию проекта в sys.path для правильного импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импорты из FastAPI

# Импорты из модулей приложения
from models.user import User

# Схемы и репозитории
from schemas.user import ChangeUserStatusRequest, LogoutResponse, TokenResponse, UserRead
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты из auth - после импорта моделей
from app.auth import (
    auth_backend,
    check_admin,
    current_active_user,
    fastapi_users,
)

# Импорты из core
from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationException,
    DatabaseException,
    PermissionDeniedException,
    UserNotFoundException,
)
from app.core.logger_config import (
    log_auth_error,
    log_auth_info,
    log_db_error,
    log_info,
    log_warning,
)

try:
    from services.user_service import UserService
except ImportError:
    # Если модули не найдены, определяем базовый класс
    class UserService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, id):
            return None

        async def update(self, user):
            pass


# Определение роутера
router = APIRouter(prefix="/users", tags=["users"])

# Добавляем маршруты fastapi-users с явным префиксом
router.include_router(
    fastapi_users.get_users_router(UserRead, UserRead),
    prefix="",  # Пустой префикс, так как базовый префикс уже /users
)


async def refresh_token(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        log_auth_info(f"Refreshing token for user: {user.email} (id: {user.id})")
        new_access_token = await auth_backend.get_strategy().write_token(user)
        log_auth_info(f"Token refreshed successfully for user: {user.email}")
        return TokenResponse(access_token=new_access_token, token_type="bearer")
    except Exception as e:
        log_auth_error(e, operation="refresh_token")
        raise AuthenticationException("Недействительный токен обновления")


async def logout(user: User = Depends(current_active_user)) -> LogoutResponse:
    """Реализация выхода из системы"""
    try:
        log_auth_info(f"User logged out: {user.email} (id: {user.id})")
        # Здесь могла бы быть реализация инвалидации токена, если бы использовалось хранилище токенов
        # Поскольку используются JWT-токены без хранения состояния,
        # то реального "выхода" не происходит - клиент просто должен удалить токен
        return LogoutResponse(detail="Successfully logged out")
    except Exception as e:
        log_auth_error(e, operation="logout")
        raise AuthenticationException("Ошибка при выходе из системы")


async def protected_route(user: User = Depends(current_active_user)) -> dict:
    try:
        log_info(f"User {user.email} accessed protected route")
        return {
            "user": user.email,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "is_verified": user.is_verified,
            "is_moderator": user.is_moderator,
        }
    except Exception as e:
        log_auth_error(e, operation="protected_route")
        raise AuthenticationException("Ошибка доступа к защищенному маршруту")


@router.patch("/{id}/status", response_model=UserRead)
async def change_user_status(
    id: int,
    change_status_req: ChangeUserStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
) -> UserRead:
    try:
        # Проверка наличия пользователя
        user_service = UserService(db)
        user = await user_service.get_by_id(id)
        if not user:
            log_warning(f"Attempted to change status for non-existent user with id: {id}")
            raise UserNotFoundException(f"Пользователь с ID {id} не найден")

        # Запрет на понижение прав самому себе
        if id == current_user.id and current_user.is_superuser and change_status_req.is_superuser is False:
            log_warning(f"Admin user {current_user.id} attempted to demote themselves")
            raise PermissionDeniedException("Администратор не может понизить свои права")

        # Обновление статуса пользователя
        update_data = {}
        if change_status_req.is_moderator is not None:
            update_data["is_moderator"] = change_status_req.is_moderator
        if change_status_req.is_superuser is not None:
            update_data["is_superuser"] = change_status_req.is_superuser

        # Применяем изменения только если есть что менять
        if update_data:
            log_info(f"Changing status for user {user.email}: {update_data}")
            for key, value in update_data.items():
                setattr(user, key, value)
            await user_service.update(user)

        return UserRead.model_validate(user)
    except (UserNotFoundException, PermissionDeniedException):
        raise
    except Exception as e:
        log_db_error(e, operation="change_user_status", table="users", user_id=str(id))
        await db.rollback()
        raise DatabaseException("Ошибка при изменении статуса пользователя")


@router.get("/{id}/status", response_model=UserRead)
async def get_user_status(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
) -> UserRead:
    user_service = UserService(db)
    user = await user_service.get_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return UserRead.model_validate(user)
