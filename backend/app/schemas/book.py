from datetime import datetime
from typing import List, Optional

from models.book import Language
from pydantic import BaseModel, ConfigDict, Field


# Базовые схемы
class AuthorBase(BaseModel):
    name: str


class BookBase(BaseModel):
    title: str = Field(max_length=50)
    year: Optional[str] = Field(None, max_length=4)
    publisher: Optional[str] = Field(None, max_length=50)
    isbn: str = Field(max_length=20)
    description: Optional[str] = Field(None, max_length=1023)
    cover: Optional[str] = Field(None, max_length=255)
    language: Language = Field(default=Language.RU)
    file_url: str = Field(max_length=255)


# Схемы для категорий и тегов
class CategoryBase(BaseModel):
    name_categories: str
    description: Optional[str] = None


class TagBase(BaseModel):
    name_tag: str


# Схемы для создания
class AuthorCreate(AuthorBase):
    pass


class BookCreate(BookBase):
    authors: List[int] = []  # Список ID авторов
    categories: List[int] = []  # Список ID категорий
    tags: List[int] = []


class CategoryCreate(CategoryBase):
    pass


class TagCreate(TagBase):
    pass


# Схемы для ответов
class AuthorResponse(AuthorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


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
    authors: List[AuthorResponse] = Field(default_factory=list)
    categories: List[CategoryResponse] = Field(default_factory=list)
    tags: List[TagResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# Схемы для обновления
class BookUpdate(BookCreate):
    pass


class BookPartial(BaseModel):
    title: Optional[str] = Field(None, max_length=50)
    year: Optional[str] = Field(None, max_length=4)
    publisher: Optional[str] = Field(None, max_length=50)
    isbn: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=1023)
    cover: Optional[str] = Field(None, max_length=255)
    language: Optional[Language] = None
    file_url: Optional[str] = Field(None, max_length=255)
    authors: Optional[List[int]] = None
    categories: Optional[List[int]] = None
    tags: Optional[List[int]] = None


# Схемы для Автора
class AuthorUpdate(AuthorBase):
    name: Optional[str] = None


class Author(AuthorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Схемы для Категории
class CategoryUpdate(CategoryBase):
    name_categories: Optional[str] = None
    description: Optional[str] = None


class Category(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Схемы для Тега
class TagUpdate(TagBase):
    name_tag: Optional[str] = None


class Tag(TagBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
