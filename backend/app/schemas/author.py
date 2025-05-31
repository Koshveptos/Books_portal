"""
Схемы данных для авторов
"""

from typing import Optional

from pydantic import BaseModel, Field


class AuthorBase(BaseModel):
    """
    Базовая схема для автора
    """

    name: str = Field(..., description="Имя автора")
    bio: Optional[str] = Field(None, description="Биография автора")


class AuthorCreate(AuthorBase):
    """
    Схема для создания автора
    """

    pass


class AuthorResponse(AuthorBase):
    """
    Схема для ответа с данными автора
    """

    id: int = Field(..., description="ID автора")

    class Config:
        from_attributes = True
