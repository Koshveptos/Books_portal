from typing import List

from auth import current_active_user
from core.database import get_db
from core.exceptions import (
    BookNotFoundException,
    DatabaseException,
    LikeAlreadyExistsException,
    LikeNotFoundException,
)
from core.logger_config import (
    log_db_error,
    log_info,
    log_warning,
)
from fastapi import APIRouter, Depends, status
from models.book import Book, likes
from models.user import User
from schemas.book import BookResponse
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/likes", tags=["likes"])


@router.post("/{book_id}", status_code=status.HTTP_200_OK)
async def like_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Поставить лайк книге.

    Этот эндпоинт добавляет книгу в список понравившихся пользователю книг,
    что влияет на рекомендации и историю активности.
    """
    try:
        log_info(f"User {current_user.id} attempting to like book {book_id}")

        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            log_warning(f"Attempt to like non-existent book: id={book_id}, user id={current_user.id}")
            raise BookNotFoundException(message=f"Книга с ID {book_id} не найдена")

        # Проверяем, есть ли уже лайк от этого пользователя
        like_query = select(likes).where((likes.c.user_id == current_user.id) & (likes.c.book_id == book_id))
        result = await db.execute(like_query)
        existing_like = result.first()

        if existing_like:
            log_info(f"Book {book_id} already liked by user {current_user.id}")
            raise LikeAlreadyExistsException(message="Вы уже лайкнули эту книгу")

        # Добавляем лайк
        insert_stmt = insert(likes).values(user_id=current_user.id, book_id=book_id)
        await db.execute(insert_stmt)
        await db.commit()

        log_info(f"User {current_user.id} liked book {book_id}")
        return {"message": "Книга добавлена в понравившиеся"}

    except (BookNotFoundException, LikeAlreadyExistsException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="like_book", table="likes", book_id=book_id, user_id=current_user.id)
        raise DatabaseException("Ошибка при добавлении лайка")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="like_book", table="likes", book_id=book_id, user_id=current_user.id)
        raise DatabaseException("Ошибка при добавлении лайка")


@router.delete("/{book_id}", status_code=status.HTTP_200_OK)
async def unlike_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Убрать лайк с книги.

    Этот эндпоинт удаляет книгу из списка понравившихся пользователю книг.
    """
    try:
        log_info(f"User {current_user.id} attempting to unlike book {book_id}")

        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            log_warning(f"Attempt to unlike non-existent book: id={book_id}, user id={current_user.id}")
            raise BookNotFoundException(message=f"Книга с ID {book_id} не найдена")

        # Удаляем лайк
        delete_stmt = delete(likes).where((likes.c.user_id == current_user.id) & (likes.c.book_id == book_id))
        result = await db.execute(delete_stmt)

        if result.rowcount == 0:
            log_warning(f"User {current_user.id} attempting to remove non-existent like from book {book_id}")
            raise LikeNotFoundException(message="Лайк не найден. Возможно, вы не лайкали эту книгу.")

        await db.commit()

        log_info(f"User {current_user.id} unliked book {book_id}")
        return {"message": "Лайк успешно удален"}

    except (BookNotFoundException, LikeNotFoundException):
        raise
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="unlike_book", table="likes", book_id=book_id, user_id=current_user.id)
        raise DatabaseException("Ошибка при удалении лайка")


@router.get("/", response_model=List[BookResponse])
async def get_liked_books(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Получить список понравившихся книг пользователя.

    Возвращает все книги, которые пользователь отметил как понравившиеся.
    """
    try:
        log_info(f"Getting liked books for user {current_user.id}")

        # Запрос для получения книг, которые лайкнул пользователь
        query = (
            select(Book)
            .join(likes, Book.id == likes.c.book_id)
            .where(likes.c.user_id == current_user.id)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
        )

        result = await db.execute(query)
        books = result.scalars().all()

        log_info(f"Found {len(books)} liked books for user {current_user.id}")

        # Преобразуем книги в модели Pydantic
        return [BookResponse.model_validate(book) for book in books]

    except Exception as e:
        log_db_error(e, operation="get_liked_books", table="likes", user_id=current_user.id)
        raise DatabaseException("Ошибка при получении списка понравившихся книг")
