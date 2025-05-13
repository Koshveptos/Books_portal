"""
Маршруты API для аутентификации пользователей
"""

from core.auth import auth_backend, current_active_user, current_required_user, fastapi_users
from fastapi import APIRouter, Depends
from models.user import User
from schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter()

# Встроенные маршруты fastapi-users
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
)

# Маршрут регистрации
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)

# Маршрут для сброса пароля
router.include_router(
    fastapi_users.get_reset_password_router(),
)

# Маршрут для верификации пользователя
router.include_router(
    fastapi_users.get_verify_router(UserRead),
)

# Маршрут для управления пользователем
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
)


@router.get("/me", response_model=UserRead)
async def get_current_user(user: User = Depends(current_required_user)):
    """
    Получить информацию о текущем пользователе.
    """
    return user


@router.get("/status", tags=["auth"])
async def auth_status(user: User = Depends(current_active_user)):
    """
    Проверка статуса аутентификации.
    Возвращает информацию о текущем пользователе, если он аутентифицирован.
    """
    if not user:
        return {"authenticated": False, "user_id": None, "email": None, "is_moderator": False, "is_superuser": False}

    return {
        "authenticated": True,
        "user_id": user.id,
        "email": user.email,
        "is_moderator": user.is_moderator,
        "is_superuser": user.is_superuser,
    }


@router.post("/check-token", tags=["auth"])
async def check_token(user: User = Depends(current_required_user)):
    """
    Проверка валидности токена.
    """
    return {"valid": True, "user_id": user.id}
