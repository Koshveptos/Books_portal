import sys
from pathlib import Path

from fastapi import APIRouter

# Добавляем корневую директорию проекта в sys.path для правильного импорта
sys.path.insert(0, str(Path(__file__).parent.parent))


from auth import auth_backend, fastapi_users
from core.exceptions import (
    AuthenticationException,
    CredentialsException,
    TokenExpiredException,
)
from core.logger_config import (
    log_auth_error,
    log_auth_info,
    log_auth_warning,
)
from schemas.user import LogoutResponse, TokenResponse, UserCreate, UserRead

from .user import logout, protected_route, refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])

# Добавляем встроенный роутер регистрации первым
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)

# Встроенные маршруты fastapi-users
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)

# Маршрут сброса пароля
router.include_router(
    fastapi_users.get_reset_password_router(),
)

# Маршрут верификации
router.include_router(
    fastapi_users.get_verify_router(UserRead),
)


# Кастомные маршруты с обработкой ошибок
@router.post("/jwt/refresh", response_model=TokenResponse)
async def refresh_token_route():
    try:
        log_auth_info("Processing token refresh request")
        return await refresh_token()
    except TokenExpiredException as e:
        log_auth_warning(f"Token refresh attempt with expired token: {str(e)}")
        raise
    except CredentialsException as e:
        log_auth_warning(f"Invalid credentials during token refresh: {str(e)}")
        raise
    except Exception as e:
        log_auth_error(e, operation="refresh_token")
        raise AuthenticationException("Ошибка при обновлении токена")


@router.post("/jwt/logout", response_model=LogoutResponse)
async def logout_route():
    try:
        log_auth_info("Processing logout request")
        return await logout()
    except Exception as e:
        log_auth_error(e, operation="logout")
        raise AuthenticationException("Ошибка при выходе из системы")


@router.get("/protected-route", response_model=dict)
async def protected_route_handler():
    try:
        log_auth_info("Accessing protected route")
        return await protected_route()
    except Exception as e:
        log_auth_error(e, operation="protected_route")
        raise AuthenticationException("Ошибка доступа к защищенному маршруту")
