from typing import Optional

from fastapi_users import schemas
from models.user import UserRole


class UserRead(schemas.BaseUser[int]):
    role: UserRole

    class Config:
        from_attributes = True


class UserCreate(schemas.BaseUserCreate):
    role: UserRole = UserRole.USER

    class Config:
        from_attributes = True


class UserUpdate(schemas.BaseUserUpdate):
    role: Optional[UserRole] = None

    class Config:
        from_attributes = True
