"""
Схемы данных для тегов
"""

from typing import Optional

from pydantic import BaseModel, Field


class TagBase(BaseModel):
    """
    Базовая схема для тега
    """

    name: str = Field(..., description="Название тега")
    description: Optional[str] = Field(None, description="Описание тега")


class TagCreate(TagBase):
    """
    Схема для создания тега
    """

    pass


class TagUpdate(TagBase):
    """
    Схема для обновления тега
    """

    name: Optional[str] = Field(None, description="Название тега")


class TagResponse(TagBase):
    """
    Схема для ответа с данными тега
    """

    id: int = Field(..., description="ID тега")

    class Config:
        from_attributes = True
