from auth import auth_backend, fastapi_users
from fastapi import APIRouter
from routers.user import logout, protected_route, refresh_token, register
from schemas.user import LogoutResponse, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
# Встроенные маршруты fastapi-users
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)

# Кастомный маршрут регистрации
router.add_api_route(
    "/register",
    register,
    methods=["POST"],
    response_model=UserRead,
)

# Остальные маршруты fastapi-users
router.include_router(
    fastapi_users.get_reset_password_router(),
)

router.include_router(
    fastapi_users.get_verify_router(UserRead),
)

# Кастомные маршруты
router.add_api_route(
    "/jwt/refresh",
    refresh_token,
    methods=["POST"],
    response_model=TokenResponse,
)

router.add_api_route(
    "/jwt/logout",
    logout,
    methods=["POST"],
    response_model=LogoutResponse,
)

router.add_api_route(
    "/protected-route",
    protected_route,
    methods=["GET"],
    response_model=dict,
)
