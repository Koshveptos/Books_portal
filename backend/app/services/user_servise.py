from auth import auth_backend, fastapi_users
from fastapi import APIRouter
from routers.user import logout, protected_route, refresh_token
from schemas.user import LogoutResponse, TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)

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
