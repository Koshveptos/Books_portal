from core.database import get_db
from fastapi import Depends
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
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


# Инициализация FastAPIUsers
fastapi_users = FastAPIUsers[User, int](
    get_user_db,
    [auth_backend],
)

# Получение текущего пользователя
current_active_user = fastapi_users.current_user(active=True)
