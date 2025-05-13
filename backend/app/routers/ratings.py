from typing import List, Optional

from auth import current_active_user
from core.database import get_db
from core.logger_config import logger
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.book import Book, Rating
from models.user import User
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/ratings", tags=["ratings"])


class RatingCreate(BaseModel):
    rating: float = Field(..., ge=1.0, le=5.0, description="Оценка книги от 1 до 5")
    comment: Optional[str] = Field(None, max_length=1000, description="Комментарий к оценке")


class RatingResponse(BaseModel):
    id: int
    book_id: int
    rating: float
    comment: Optional[str] = None
    user_id: int

    class Config:
        from_attributes = True


@router.post("/{book_id}", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_book(
    book_id: int,
    rating_data: RatingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Оценить книгу.

    Этот эндпоинт позволяет пользователю поставить оценку книге и оставить комментарий.
    Если пользователь уже оценивал эту книгу, его оценка обновляется.
    """
    try:
        # Проверяем, существует ли книга
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            logger.warning(f"Попытка оценить несуществующую книгу: id={book_id}, пользователь id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")

        # Проверяем, оценивал ли пользователь эту книгу раньше
        existing_rating_query = select(Rating).where((Rating.user_id == current_user.id) & (Rating.book_id == book_id))
        result = await db.execute(existing_rating_query)
        existing_rating = result.scalar_one_or_none()

        if existing_rating:
            # Обновляем существующую оценку
            existing_rating.rating = rating_data.rating
            existing_rating.comment = rating_data.comment
            await db.commit()
            await db.refresh(existing_rating)

            logger.info(
                f"Пользователь {current_user.id} обновил оценку для книги {book_id}: "
                f"с {existing_rating.rating} на {rating_data.rating}"
            )

            return existing_rating
        else:
            # Создаем новую оценку
            new_rating = Rating(
                user_id=current_user.id, book_id=book_id, rating=rating_data.rating, comment=rating_data.comment
            )

            db.add(new_rating)
            await db.commit()
            await db.refresh(new_rating)

            logger.info(f"Пользователь {current_user.id} оценил книгу {book_id} на {rating_data.rating}")

            return new_rating

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при создании оценки: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера")


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rating(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Удалить оценку книги.

    Этот эндпоинт позволяет пользователю удалить свою оценку книги.
    """
    try:
        # Находим оценку пользователя для этой книги
        rating_query = select(Rating).where((Rating.user_id == current_user.id) & (Rating.book_id == book_id))
        result = await db.execute(rating_query)
        rating = result.scalar_one_or_none()

        if not rating:
            logger.warning(f"Пользователь {current_user.id} пытается удалить несуществующую оценку для книги {book_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Оценка не найдена. Возможно, вы не оценивали эту книгу."
            )

        await db.delete(rating)
        await db.commit()

        logger.info(f"Пользователь {current_user.id} удалил оценку для книги {book_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при удалении оценки: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера")


@router.get("/", response_model=List[RatingResponse])
async def get_user_ratings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
    min_rating: Optional[float] = Query(None, ge=1.0, le=5.0, description="Минимальная оценка для фильтрации"),
    max_rating: Optional[float] = Query(None, ge=1.0, le=5.0, description="Максимальная оценка для фильтрации"),
):
    """
    Получить список оценок пользователя.

    Возвращает все оценки, которые пользователь поставил книгам.
    """
    try:
        # Базовый запрос для получения оценок пользователя
        query = select(Rating).where(Rating.user_id == current_user.id)

        # Добавляем фильтры, если они указаны
        if min_rating is not None:
            query = query.where(Rating.rating >= min_rating)

        if max_rating is not None:
            query = query.where(Rating.rating <= max_rating)

        # Сортируем по дате создания (по убыванию)
        query = query.order_by(Rating.created_at.desc())

        result = await db.execute(query)
        ratings = result.scalars().all()

        logger.info(f"Получено {len(ratings)} оценок пользователя {current_user.id}")

        return ratings

    except Exception as e:
        logger.error(f"Ошибка при получении оценок: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера")
