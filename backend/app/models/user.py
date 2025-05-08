from fastapi_users.db import SQLAlchemyBaseUserTable
from models.base import Base
from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column


class User(Base, SQLAlchemyBaseUserTable[int]):
    is_moderator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
