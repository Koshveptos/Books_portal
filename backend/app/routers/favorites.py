from typing import List

from auth import current_active_user
from core.database import get_db
from core.exceptions import (
    BookNotFoundException,
    DatabaseException,
    FavoriteAlreadyExistsException,
    FavoriteNotFoundException,
)
from core.logger_config import (
    log_db_error,
    log_info,
    log_warning,
)
from fastapi import APIRouter, Depends, status
from models.book import Book, favorites
from models.user import User
from schemas.book import BookResponse
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/{book_id}", status_code=status.HTTP_200_OK)
async def add_to_favorites(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Добавить книгу в избранное.

    Этот эндпоинт добавляет книгу в список избранных книг пользователя,
    что влияет на рекомендации и сохраняет книгу для быстрого доступа.
    """
    try:
        log_info(f"User {current_user.id} attempting to add book {book_id} to favorites")

        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            log_warning(f"Attempt to add non-existent book to favorites: id={book_id}, user id={current_user.id}")
            raise BookNotFoundException(message=f"Книга с ID {book_id} не найдена")

        # Проверяем, есть ли уже эта книга в избранном
        favorite_query = select(favorites).where(
            (favorites.c.user_id == current_user.id) & (favorites.c.book_id == book_id)
        )
        result = await db.execute(favorite_query)
        existing_favorite = result.first()

        if existing_favorite:
            log_info(f"Book {book_id} already in favorites for user {current_user.id}")
            raise FavoriteAlreadyExistsException(message="Книга уже в избранном")

        # Добавляем в избранное
        insert_stmt = insert(favorites).values(user_id=current_user.id, book_id=book_id)
        await db.execute(insert_stmt)
        await db.commit()

        log_info(f"User {current_user.id} added book {book_id} to favorites")
        return {"message": "Книга добавлена в избранное"}

    except (BookNotFoundException, FavoriteAlreadyExistsException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="add_to_favorites", table="favorites", book_id=book_id, user_id=current_user.id)
        raise DatabaseException("Ошибка при добавлении в избранное")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="add_to_favorites", table="favorites", book_id=book_id, user_id=current_user.id)
        raise DatabaseException("Ошибка при добавлении в избранное")


@router.delete("/{book_id}", status_code=status.HTTP_200_OK)
async def remove_from_favorites(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Удалить книгу из избранного.

    Этот эндпоинт удаляет книгу из списка избранных книг пользователя.
    """
    try:
        log_info(f"User {current_user.id} attempting to remove book {book_id} from favorites")

        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            log_warning(f"Attempt to remove non-existent book from favorites: id={book_id}, user id={current_user.id}")
            raise BookNotFoundException(message=f"Книга с ID {book_id} не найдена")

        # Удаляем из избранного
        delete_stmt = delete(favorites).where(
            (favorites.c.user_id == current_user.id) & (favorites.c.book_id == book_id)
        )
        result = await db.execute(delete_stmt)

        if result.rowcount == 0:
            log_warning(f"User {current_user.id} attempting to remove non-existent favorite book {book_id}")
            raise FavoriteNotFoundException(message="Книга не найдена в избранном")

        await db.commit()

        log_info(f"User {current_user.id} removed book {book_id} from favorites")
        return {"message": "Книга удалена из избранного"}

    except (BookNotFoundException, FavoriteNotFoundException):
        raise
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="remove_from_favorites", table="favorites", book_id=book_id, user_id=current_user.id)
        raise DatabaseException("Ошибка при удалении из избранного")


@router.get("/", response_model=List[BookResponse])
async def get_favorite_books(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Получить список избранных книг пользователя.

    Возвращает все книги, которые пользователь добавил в избранное.
    """
    try:
        log_info(f"Getting favorite books for user {current_user.id}")

        # Запрос для получения книг из избранного пользователя
        query = (
            select(Book)
            .join(favorites, Book.id == favorites.c.book_id)
            .where(favorites.c.user_id == current_user.id)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
        )

        result = await db.execute(query)
        books = result.scalars().all()

        log_info(f"Found {len(books)} favorite books for user {current_user.id}")

        # Преобразуем книги в модели Pydantic
        return [BookResponse.model_validate(book) for book in books]

    except Exception as e:
        log_db_error(e, operation="get_favorite_books", table="favorites", user_id=current_user.id)
        raise DatabaseException("Ошибка при получении списка избранных книг")
