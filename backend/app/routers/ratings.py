import json
from typing import List, Optional

from auth import current_active_user
from core.database import get_db
from core.dependencies import get_redis_client
from core.exceptions import (
    BookNotFoundException,
    DatabaseException,
    InvalidRatingValueException,
    RatingNotFoundException,
)
from core.logger_config import (
    log_cache_error,
    log_db_error,
    log_info,
    log_warning,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.book import Book, Rating
from models.user import User
from pydantic import BaseModel, Field
from redis import Redis
from schemas.interactions import RatingResponse
from services.interactions import InteractionsService
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from utils.json_serializer import deserialize_from_json, serialize_to_json

router = APIRouter(prefix="/ratings", tags=["ratings"])


class RatingCreate(BaseModel):
    rating: float = Field(..., ge=1.0, le=5.0, description="Оценка книги от 1 до 5")
    comment: Optional[str] = Field(None, max_length=1000, description="Комментарий к оценке")


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
        log_info(f"User {current_user.id} attempting to rate book {book_id}")

        # Проверяем, существует ли книга
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            log_warning(f"Attempt to rate non-existent book: id={book_id}, user id={current_user.id}")
            raise BookNotFoundException(message=f"Книга с ID {book_id} не найдена")

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

            log_info(
                f"User {current_user.id} updated rating for book {book_id}: "
                f"from {existing_rating.rating} to {rating_data.rating}"
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

            log_info(f"User {current_user.id} rated book {book_id} with {rating_data.rating}")

            return new_rating

    except (BookNotFoundException, InvalidRatingValueException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="rate_book", table="ratings", book_id=book_id, user_id=current_user.id)
        raise InvalidRatingValueException("Ошибка при создании оценки")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="rate_book", table="ratings", book_id=book_id, user_id=current_user.id)
        raise DatabaseException("Ошибка при создании оценки")


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
        log_info(f"User {current_user.id} attempting to delete rating for book {book_id}")

        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            log_warning(f"Attempt to delete rating for non-existent book: id={book_id}, user id={current_user.id}")
            raise BookNotFoundException(message=f"Книга с ID {book_id} не найдена")

        # Находим оценку пользователя для этой книги
        rating_query = select(Rating).where((Rating.user_id == current_user.id) & (Rating.book_id == book_id))
        result = await db.execute(rating_query)
        rating = result.scalar_one_or_none()

        if not rating:
            log_warning(f"User {current_user.id} attempting to delete non-existent rating for book {book_id}")
            raise RatingNotFoundException(message="Оценка не найдена. Возможно, вы не оценивали эту книгу.")

        await db.delete(rating)
        await db.commit()

        log_info(f"User {current_user.id} deleted rating for book {book_id}")

        return None

    except (BookNotFoundException, RatingNotFoundException):
        raise
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="delete_rating", table="ratings", book_id=book_id, user_id=current_user.id)
        raise DatabaseException("Ошибка при удалении оценки")


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
        log_info(f"Getting ratings for user {current_user.id}")

        # Базовый запрос для получения оценок пользователя
        query = select(Rating).where(Rating.user_id == current_user.id)

        # Добавляем фильтры, если они указаны
        if min_rating is not None:
            query = query.where(Rating.rating >= min_rating)
            log_info(f"Filtering by minimum rating: {min_rating}")

        if max_rating is not None:
            query = query.where(Rating.rating <= max_rating)
            log_info(f"Filtering by maximum rating: {max_rating}")

        # Сортируем по дате создания (по убыванию)
        query = query.order_by(Rating.created_at.desc())

        result = await db.execute(query)
        ratings = result.scalars().all()

        log_info(f"Found {len(ratings)} ratings for user {current_user.id}")

        return ratings

    except Exception as e:
        log_db_error(e, operation="get_user_ratings", table="ratings", user_id=current_user.id)
        raise DatabaseException("Ошибка при получении списка оценок")


@router.get("/{rating_id}", response_model=RatingResponse)
async def get_rating(
    rating_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> RatingResponse:
    """
    Получение рейтинга по ID.

    Args:
        rating_id: ID рейтинга
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        RatingResponse: Информация о рейтинге

    Raises:
        HTTPException: Если рейтинг не найден или произошла ошибка
    """
    try:
        # Пытаемся получить из кэша
        if redis_client is not None:
            try:
                cache_key = f"rating:{rating_id}"
                cached_rating = await redis_client.get(cache_key)
                if cached_rating:
                    try:
                        rating_data = deserialize_from_json(cached_rating)
                        log_info(f"Successfully retrieved rating {rating_id} from cache")
                        return RatingResponse(**rating_data)
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_rating",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_rating",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем рейтинг из БД
        interactions_service = InteractionsService(db)
        ratings = await interactions_service.get_user_ratings(user_id=None, book_id=rating_id)
        if not ratings:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Рейтинг с ID {rating_id} не найден")

        # Преобразуем в Pydantic модель
        rating_response = RatingResponse.model_validate(ratings[0])

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(rating_response),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached rating {rating_id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_rating",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return rating_response
    except HTTPException:
        raise
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_rating",
                "rating_id": rating_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении рейтинга")


@router.get("/", response_model=List[RatingResponse])
async def get_ratings(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> List[RatingResponse]:
    """
    Получение списка рейтингов с пагинацией.

    Args:
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        List[RatingResponse]: Список рейтингов

    Raises:
        HTTPException: Если произошла ошибка при получении рейтингов
    """
    try:
        # Пытаемся получить из кэша
        if redis_client is not None:
            try:
                cache_key = f"ratings:list:{skip}:{limit}"
                cached_ratings = await redis_client.get(cache_key)
                if cached_ratings:
                    try:
                        ratings_data = deserialize_from_json(cached_ratings)
                        log_info(f"Successfully retrieved {len(ratings_data)} ratings from cache")
                        return [RatingResponse(**rating) for rating in ratings_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_ratings",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_ratings",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем рейтинги из БД
        interactions_service = InteractionsService(db)
        ratings = await interactions_service.get_book_ratings(book_id=None, skip=skip, limit=limit)

        # Преобразуем в Pydantic модели
        rating_responses = [RatingResponse.model_validate(rating) for rating in ratings]

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(rating_responses),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached {len(rating_responses)} ratings")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_ratings",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return rating_responses
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_ratings",
                "skip": skip,
                "limit": limit,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении списка рейтингов"
        )
