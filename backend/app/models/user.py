from typing import TYPE_CHECKING, List

from fastapi_users.db import SQLAlchemyBaseUserTable
from models.base import Base
from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Условный импорт для аннотаций типов, чтобы избежать циклических импортов
if TYPE_CHECKING:
    from models.book import Rating


class User(Base, SQLAlchemyBaseUserTable[int]):
    is_moderator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Отношения
    ratings: Mapped[List["Rating"]] = relationship("Rating", back_populates="user", cascade="all, delete-orphan")
