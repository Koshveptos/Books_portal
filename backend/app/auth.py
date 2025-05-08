from core.database import get_db
from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers
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


# Кастомный UserManager
class UserManager(BaseUserManager[User, int]):
    async def create(self, user_create, **kwargs):
        user_dict = user_create.dict(exclude_unset=True)
        # Запрещаем регистрацию с is_moderator=True или is_superuser=True
        if user_dict.get("is_moderator", False) or user_dict.get("is_superuser", False):
            raise ValueError("Cannot register as moderator or superuser")
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)
        created_user = await self.user_db.create(user_dict)
        await self.on_after_register(created_user, None)
        return created_user

    async def update(self, user_update, user, **kwargs):
        # Проверяем, что только суперпользователь может менять is_moderator или is_superuser
        if not user.is_superuser:
            user_dict = user_update.dict(exclude_unset=True)
            if "is_moderator" in user_dict or "is_superuser" in user_dict:
                raise ValueError("Only superusers can update moderator or superuser status")
        return await super().update(user_update, user, **kwargs)


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


# Инициализация FastAPIUsers
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# Получение текущего пользователя
current_active_user = fastapi_users.current_user(active=True)
