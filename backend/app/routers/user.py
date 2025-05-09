from uuid import UUID

from auth import auth_backend, check_admin, current_active_user, fastapi_users
from core.database import get_db
from core.exceptions import (
    InvalidUserDataException,
    UserAlreadyExistsException,
)
from core.logger_config import logger
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users.exceptions import UserAlreadyExists
from models.user import User
from schemas.user import ChangeUserStatusRequest, LogoutResponse, TokenResponse, UserCreate, UserRead
from services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession

# Определение роутера
router = APIRouter(tags=["users"])


async def refresh_token(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        logger.info(f"Refreshing token for user: {user.email} (id: {user.id})")
        new_access_token = await auth_backend.get_strategy().write_token(user)
        logger.info(f"Token refreshed successfully for user: {user.email}")
        return TokenResponse(access_token=new_access_token, token_type="bearer")
    except Exception as e:
        logger.error(f"Error refreshing token for user {user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


async def logout(user: User = Depends(current_active_user)) -> LogoutResponse:
    """Реализация выхода из системы"""
    try:
        logger.info(f"User logged out: {user.email} (id: {user.id})")
        # Здесь могла бы быть реализация инвалидации токена, если бы использовалось хранилище токенов
        # Поскольку используются JWT-токены без хранения состояния,
        # то реального "выхода" не происходит - клиент просто должен удалить токен
        return LogoutResponse(detail="Successfully logged out")
    except Exception as e:
        logger.error(f"Error during logout for user {user.email}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error during logout process")


async def protected_route(user: User = Depends(current_active_user)) -> dict:
    logger.debug(f"User {user.email} accessed protected route")
    return {
        "user": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "is_verified": user.is_verified,
        "is_moderator": user.is_moderator,
    }


async def register(
    user_create: UserCreate,
    user_manager=Depends(fastapi_users.get_user_manager),
) -> UserRead:
    try:
        logger.info(f"Registering new user: {user_create.email}")
        created_user = await user_manager.create(user_create)
        logger.info(f"User registered successfully: {created_user.email} (id: {created_user.id})")
        return UserRead.model_validate(created_user)
    except UserAlreadyExists:
        logger.warning(f"Registration failed: User with email {user_create.email} already exists")
        raise UserAlreadyExistsException()
    except ValueError as e:
        logger.warning(f"Registration failed for {user_create.email}: {str(e)}")
        raise InvalidUserDataException(message=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during registration for {user_create.email}: {str(e)}")
        raise InvalidUserDataException(message=f"Ошибка при регистрации: {str(e)}")


@router.patch("/{id}/status", response_model=UserRead)
async def change_user_status(
    id: UUID,
    change_status_req: ChangeUserStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),
) -> UserRead:
    try:
        # Проверка наличия пользователя
        user_service = UserService(db)
        user = await user_service.get_by_id(id)
        if not user:
            logger.warning(f"Attempted to change status for non-existent user with id: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Запрет на понижение прав самому себе
        if id == current_user.id and current_user.is_superuser and change_status_req.is_superuser is False:
            logger.warning(f"Admin user {current_user.id} attempted to demote themselves")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin cannot demote themselves",
            )

        # Обновление статуса пользователя
        update_data = {}
        if change_status_req.is_moderator is not None:
            update_data["is_moderator"] = change_status_req.is_moderator
        if change_status_req.is_superuser is not None:
            update_data["is_superuser"] = change_status_req.is_superuser

        # Применяем изменения только если есть что менять
        if update_data:
            logger.info(f"Changing status for user {user.email}: {update_data}")
            for key, value in update_data.items():
                setattr(user, key, value)
            await user_service.update(user)

        return UserRead.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing status for user {id}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error changing user status",
        )
