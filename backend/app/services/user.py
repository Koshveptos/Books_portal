from fastapi import Depends
from fastapi_users import BaseUserManager
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db


class UserService(BaseUserManager[User, int]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    async def on_after_register(self, user: User, request=None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(self, user: User, token: str, request=None):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(self, user: User, token: str, request=None):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_service(db: AsyncSession = Depends(get_db)):
    yield UserService(db)
