from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RecommendationType(str, Enum):
    """Типы рекомендаций"""

    HYBRID = "hybrid"
    COLLABORATIVE = "collaborative"
    CONTENT = "content"
    POPULARITY = "popularity"
    AUTHOR = "author"
    CATEGORY = "category"
    TAG = "tag"
    RANDOM = "random"


class SimilarUser(BaseModel):
    """Похожий пользователь для коллаборативной фильтрации"""

    id: int = Field(..., description="ID пользователя")
    username: Optional[str] = Field(None, description="Имя пользователя")
    email: Optional[str] = Field(None, description="Email пользователя")
    similarity: float = Field(..., description="Оценка сходства с текущим пользователем")
    common_books: int = Field(..., description="Количество общих книг с текущим пользователем")


class BookRecommendation(BaseModel):
    """Модель рекомендации книги"""

    id: int = Field(..., description="ID книги")
    book_id: int = Field(..., description="ID книги (дублирует id для совместимости)")
    title: str = Field(..., description="Название книги")
    author: str = Field(..., description="Автор книги")
    author_names: List[str] = Field(default_factory=list, description="Список авторов книги")
    category: Optional[str] = Field(None, description="Категория книги")
    year: Optional[int] = Field(None, description="Год издания")
    cover: Optional[str] = Field(None, description="URL обложки книги")
    rating: Optional[float] = Field(None, description="Средний рейтинг книги")
    score: float = Field(..., description="Оценка релевантности рекомендации")
    reason: str = Field(..., description="Причина рекомендации")
    recommendation_type: RecommendationType = Field(..., description="Тип рекомендации")
    similar_users: List[SimilarUser] = Field(
        default_factory=list, description="Похожие пользователи (для коллаборативной фильтрации)"
    )

    model_config = ConfigDict(from_attributes=True)


class RecommendationStats(BaseModel):
    """Статистика рекомендаций для пользователя"""

    user_id: int = Field(..., description="ID пользователя")
    rated_books_count: int = Field(..., description="Количество оцененных книг")
    total_books_count: int = Field(..., description="Общее количество книг в системе")
    avg_rating: float = Field(..., description="Средний рейтинг пользователя")
    favorite_authors: List[str] = Field(default_factory=list, description="Любимые авторы")
    favorite_categories: List[str] = Field(default_factory=list, description="Любимые категории")
    favorite_tags: List[str] = Field(default_factory=list, description="Любимые теги")
    is_collaborative_ready: bool = Field(..., description="Готовность к коллаборативным рекомендациям")
    is_content_ready: bool = Field(..., description="Готовность к контентным рекомендациям")


class UserModelState(BaseModel):
    """Состояние модели рекомендаций для пользователя"""

    user_id: int = Field(..., description="ID пользователя")
    last_update: str = Field(..., description="Дата последнего обновления")
    model_version: str = Field(..., description="Версия модели")
    is_trained: bool = Field(..., description="Флаг обучения модели")
