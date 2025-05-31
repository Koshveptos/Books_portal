from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Определяем собственный Enum для языка книги в схемах
class Language(str, Enum):
    RU = "ru"
    EN = "en"


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
    language: str = Field(default="ru", description="Book language, 'ru' or 'en'")
    file_url: str = Field(max_length=255)

    @field_validator("language")
    @classmethod
    def normalize_language_to_lowercase_string(cls, v: Any) -> str:
        logger.debug(f"Pydantic validator normalize_language_to_lowercase_string received: {v} (type: {type(v)})")
        if v is None:
            logger.debug("Pydantic validator returning default 'ru' for None input.")
            return "ru"  # Значение по умолчанию

        value_str = ""
        if isinstance(v, Language):  # Если это наш Language enum из models.book
            value_str = v.value  # Используем .value ('ru' или 'en')
            logger.debug(f"Input is Language enum, value_str set to: {value_str}")
        elif isinstance(v, str):
            value_str = v.lower()
            logger.debug(f"Input is string, value_str (lowercased) set to: {value_str}")
        else:
            value_str = str(v).lower()
            logger.debug(f"Input is other type, value_str (converted and lowercased) set to: {value_str}")

        if value_str not in ["ru", "en"]:
            logger.error(f"Invalid language value after normalization: '{value_str}'. Raising ValueError.")
            raise ValueError(f"Invalid language: '{value_str}'. Must be 'ru' or 'en'.")
        logger.debug(f"Pydantic validator returning: {value_str}")
        return value_str


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
    language: Language
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
    language: Optional[str] = Field(None, description="Book language, 'ru' or 'en'")
    file_url: Optional[str] = Field(None, max_length=255)
    authors: Optional[List[int]] = None
    categories: Optional[List[int]] = None
    tags: Optional[List[int]] = None

    @field_validator("language", check_fields=False)
    @classmethod
    def normalize_optional_language_to_lowercase_string(cls, v: Any) -> Optional[str]:
        logger.debug(
            f"Pydantic validator normalize_optional_language_to_lowercase_string received: {v} (type: {type(v)})"
        )
        if v is None:
            logger.debug("Pydantic validator returning None for optional language.")
            return None

        value_str = ""
        if isinstance(v, Language):
            value_str = v.value
            logger.debug(f"Optional input is Language enum, value_str set to: {value_str}")
        elif isinstance(v, str):
            value_str = v.lower()
            logger.debug(f"Optional input is string, value_str (lowercased) set to: {value_str}")
        else:
            value_str = str(v).lower()
            logger.debug(f"Optional input is other type, value_str (converted and lowercased) set to: {value_str}")

        if value_str not in ["ru", "en"]:
            logger.error(f"Invalid optional language value after normalization: '{value_str}'. Raising ValueError.")
            raise ValueError(f"Invalid language: '{value_str}'. Must be 'ru' or 'en'.")
        logger.debug(f"Pydantic validator returning for optional: {value_str}")
        return value_str


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


# Схема для результатов поиска
class BookSearchResponse(BaseModel):
    total: int
    items: List[BookResponse]
    page: int = 1
    size: int = 10
    filters: Dict[str, Any] = Field(default_factory=dict)
    query: Optional[str] = None


class UserRatingResponse(BaseModel):
    """
    Схема для ответа с книгой и оценкой пользователя.
    """

    book: BookResponse
    user_rating: float = Field(..., description="Оценка пользователя", ge=1, le=5)
