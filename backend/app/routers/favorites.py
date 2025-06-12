import json
from typing import List

from auth import current_active_user
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.book import Book, favorites
from models.user import User
from redis import Redis
from schemas.book import BookResponse
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_redis_client
from app.core.logger_config import (
    log_cache_error,
    log_db_error,
    log_info,
    log_warning,
)
from app.utils.json_serializer import deserialize_from_json, serialize_to_json

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/{book_id}", status_code=status.HTTP_200_OK)
async def add_to_favorites(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
    redis_client: Redis = Depends(get_redis_client),
):
    """
    Добавить книгу в избранное.

    Args:
        book_id: ID книги
        db: Сессия базы данных
        current_user: Текущий пользователь
        redis_client: Клиент Redis

    Returns:
        dict: Сообщение об успешном добавлении

    Raises:
        HTTPException: Если книга не найдена или уже в избранном
    """
    try:
        log_info(f"User {current_user.id} attempting to add book {book_id} to favorites")

        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            log_warning(f"Attempt to add non-existent book to favorites: id={book_id}, user id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Книга с ID {book_id} не найдена")

        # Проверяем, есть ли уже эта книга в избранном
        favorite_query = select(favorites).where(
            (favorites.c.user_id == current_user.id) & (favorites.c.book_id == book_id)
        )
        result = await db.execute(favorite_query)
        existing_favorite = result.first()

        if existing_favorite:
            log_info(f"Book {book_id} already in favorites for user {current_user.id}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Книга уже в избранном")

        # Добавляем в избранное
        insert_stmt = insert(favorites).values(user_id=current_user.id, book_id=book_id)
        await db.execute(insert_stmt)
        await db.commit()

        # Инвалидируем кэш избранных книг пользователя
        if redis_client is not None:
            try:
                cache_key = f"favorites:{current_user.id}:*"
                await redis_client.delete_pattern(cache_key)
                log_info(f"Invalidated favorites cache for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "invalidate_favorites_cache",
                        "user_id": current_user.id,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        log_info(f"User {current_user.id} added book {book_id} to favorites")
        return {"message": "Книга добавлена в избранное"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        log_db_error(
            e,
            {
                "operation": "add_to_favorites",
                "book_id": book_id,
                "user_id": current_user.id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при добавлении в избранное"
        )


@router.delete("/{book_id}", status_code=status.HTTP_200_OK)
async def remove_from_favorites(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
    redis_client: Redis = Depends(get_redis_client),
):
    """
    Удалить книгу из избранного.

    Args:
        book_id: ID книги
        db: Сессия базы данных
        current_user: Текущий пользователь
        redis_client: Клиент Redis

    Returns:
        dict: Сообщение об успешном удалении

    Raises:
        HTTPException: Если книга не найдена или не в избранном
    """
    try:
        log_info(f"User {current_user.id} attempting to remove book {book_id} from favorites")

        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            log_warning(f"Attempt to remove non-existent book from favorites: id={book_id}, user id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Книга с ID {book_id} не найдена")

        # Удаляем из избранного
        delete_stmt = delete(favorites).where(
            (favorites.c.user_id == current_user.id) & (favorites.c.book_id == book_id)
        )
        result = await db.execute(delete_stmt)

        if result.rowcount == 0:
            log_warning(f"User {current_user.id} attempting to remove non-existent favorite book {book_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена в избранном")

        await db.commit()

        # Инвалидируем кэш избранных книг пользователя
        if redis_client is not None:
            try:
                cache_key = f"favorites:{current_user.id}:*"
                await redis_client.delete_pattern(cache_key)
                log_info(f"Invalidated favorites cache for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "invalidate_favorites_cache",
                        "user_id": current_user.id,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        log_info(f"User {current_user.id} removed book {book_id} from favorites")
        return {"message": "Книга удалена из избранного"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        log_db_error(
            e,
            {
                "operation": "remove_from_favorites",
                "book_id": book_id,
                "user_id": current_user.id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при удалении из избранного"
        )


@router.get("/", response_model=List[BookResponse])
async def get_favorite_books(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
    redis_client: Redis = Depends(get_redis_client),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество записей"),
):
    """
    Получить список избранных книг пользователя.

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        redis_client: Клиент Redis
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей

    Returns:
        List[BookResponse]: Список избранных книг

    Raises:
        HTTPException: Если произошла ошибка при получении списка
    """
    try:
        log_info(f"Getting favorite books for user {current_user.id}")

        # Пытаемся получить из кэша
        if redis_client is not None:
            try:
                cache_key = f"favorites:{current_user.id}:{skip}:{limit}"
                cached_favorites = await redis_client.get(cache_key)
                if cached_favorites:
                    try:
                        favorites_data = deserialize_from_json(cached_favorites)
                        log_info(
                            f"Successfully retrieved {len(favorites_data)} favorites from cache for user {current_user.id}"
                        )
                        return [BookResponse(**book) for book in favorites_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_favorites",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_favorites",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Запрос для получения книг из избранного пользователя
        query = (
            select(Book)
            .join(favorites, Book.id == favorites.c.book_id)
            .where(favorites.c.user_id == current_user.id)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        books = result.scalars().all()

        log_info(f"Found {len(books)} favorite books for user {current_user.id}")

        # Преобразуем книги в модели Pydantic
        favorite_responses = [BookResponse.model_validate(book) for book in books]

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(favorite_responses),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached {len(favorite_responses)} favorites for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_favorites",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return favorite_responses

    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_favorite_books",
                "user_id": current_user.id,
                "skip": skip,
                "limit": limit,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении списка избранных книг"
        )
