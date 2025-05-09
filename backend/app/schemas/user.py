from typing import Optional

from fastapi_users import schemas
from pydantic import BaseModel


class UserRead(schemas.BaseUser[int]):
    is_moderator: bool


class UserCreate(schemas.BaseUserCreate):
    is_moderator: Optional[bool] = False


class UserUpdate(schemas.BaseUserUpdate):
    is_moderator: Optional[bool] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    detail: str


class ChangeUserStatusRequest(BaseModel):
    is_moderator: Optional[bool] = None
    is_superuser: Optional[bool] = None
