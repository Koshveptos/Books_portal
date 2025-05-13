"""
Схемы данных для категорий
"""

from typing import Optional

from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    """
    Базовая схема для категории
    """

    name: str = Field(..., description="Название категории")
    description: Optional[str] = Field(None, description="Описание категории")


class CategoryCreate(CategoryBase):
    """
    Схема для создания категории
    """

    pass


class CategoryUpdate(CategoryBase):
    """
    Схема для обновления категории
    """

    name: Optional[str] = Field(None, description="Название категории")


class CategoryResponse(CategoryBase):
    """
    Схема для ответа с данными категории
    """

    id: int = Field(..., description="ID категории")

    class Config:
        from_attributes = True
