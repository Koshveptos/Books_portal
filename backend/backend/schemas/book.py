from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# Базовые схемы
class BookBase(BaseModel):
    title: str = Field(max_length=50)
    author: str = Field(max_length=50)
    year: Optional[str] = Field(None, max_length=4)
    publisher: Optional[str] = Field(None, max_length=50)
    isbn: str = Field(max_length=20)
    description: Optional[str] = Field(None, max_length=1023)
    cover: Optional[str] = Field(None, max_length=255)
    language: Optional[str] = Field(None, max_length=50)
    file_url: str = Field(max_length=255)


# Схемы для категорий и тегов
class CategoryBase(BaseModel):
    name_categories: str = Field(max_length=50)
    description: Optional[str] = Field(None, max_length=255)


class TagBase(BaseModel):
    name_tag: str = Field(max_length=50)


# Схемы для создания
class BookCreate(BookBase):
    categories: List[int] = []  # Список ID категорий
    tags: List[int] = []


class CategoryCreate(CategoryBase):
    pass


class TagCreate(TagBase):
    pass


# Схемы для ответов
class CategoryResponse(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TagResponse(TagBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class BookResponse(BookBase):
    id: int
    created_at: datetime
    updated_at: datetime
    categories: List[CategoryResponse] = Field(default_factory=list)
    tags: List[TagResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# Схемы для обновления
class BookUpdate(BookCreate):
    pass


class BookPartial(BaseModel):
    title: Optional[str] = Field(None, max_length=50)
    author: Optional[str] = Field(None, max_length=50)
    year: Optional[str] = Field(None, max_length=4)
    publisher: Optional[str] = Field(None, max_length=50)
    isbn: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=1023)
    cover: Optional[str] = Field(None, max_length=255)
    language: Optional[str] = Field(None, max_length=50)
    file_url: Optional[str] = Field(None, max_length=255)
    categories: Optional[List[int]] = None
    tags: Optional[List[int]] = None
