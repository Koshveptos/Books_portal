import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для правильного импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

# Теперь импортируем из глобальной области видимости
from auth import auth_backend, fastapi_users
from core.exceptions import (
    AuthenticationException,
    CredentialsException,
    TokenExpiredException,
    UserAlreadyExistsException,
    ValidationException,
)
from core.logger_config import (
    log_auth_error,
    log_auth_info,
    log_auth_warning,
    log_validation_error,
)
from fastapi import APIRouter
from schemas.user import LogoutResponse, TokenResponse, UserRead

# Импортируем пользовательские функции после импорта auth
from .user import logout, protected_route, refresh_token, register

router = APIRouter(prefix="/auth", tags=["auth"])

# Встроенные маршруты fastapi-users
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)


# Кастомный маршрут регистрации с обработкой ошибок
@router.post("/register", response_model=UserRead)
async def register_route():
    try:
        log_auth_info("Processing registration request")
        return await register()
    except UserAlreadyExistsException as e:
        log_auth_warning(f"Registration attempt with existing email: {str(e)}")
        raise
    except ValidationException as e:
        log_validation_error(e, model_name="User", field="registration")
        raise
    except Exception as e:
        log_auth_error(e, operation="register")
        raise AuthenticationException("Ошибка при регистрации пользователя")


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
