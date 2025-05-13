from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RatingBase(BaseModel):
    """
    Базовая схема для оценок книг.
    """

    book_id: int
    rating: float = Field(..., ge=1, le=5, description="Оценка книги от 1 до 5")
    comment: Optional[str] = Field(None, max_length=500, description="Комментарий к оценке")


class RatingCreate(RatingBase):
    """
    Схема для создания оценки книги.
    """

    pass


class RatingResponse(RatingBase):
    """
    Схема для ответа с оценкой книги.
    """

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LikeResponse(BaseModel):
    """
    Схема для ответа с информацией о лайке.
    """

    book_id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class FavoriteResponse(BaseModel):
    """
    Схема для ответа с информацией об избранном.
    """

    book_id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
