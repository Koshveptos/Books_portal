from typing import List

from auth import current_active_user
from core.database import get_db
from core.logger_config import logger
from fastapi import APIRouter, Depends, HTTPException, status
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
        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            logger.warning(f"Попытка лайкнуть несуществующую книгу: id={book_id}, пользователь id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")

        # Проверяем, есть ли уже лайк от этого пользователя
        like_query = select(likes).where((likes.c.user_id == current_user.id) & (likes.c.book_id == book_id))
        result = await db.execute(like_query)
        existing_like = result.first()

        if existing_like:
            logger.info(f"Книга {book_id} уже лайкнута пользователем {current_user.id}")
            return {"message": "Вы уже лайкнули эту книгу"}

        # Добавляем лайк
        insert_stmt = insert(likes).values(user_id=current_user.id, book_id=book_id)
        await db.execute(insert_stmt)
        await db.commit()

        logger.info(f"Пользователь {current_user.id} лайкнул книгу {book_id}")
        return {"message": "Книга добавлена в понравившиеся"}

    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Ошибка целостности при добавлении лайка: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ошибка при добавлении лайка")
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при добавлении лайка: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера")


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
        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            logger.warning(
                f"Попытка убрать лайк с несуществующей книги: id={book_id}, пользователь id={current_user.id}"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")

        # Удаляем лайк
        delete_stmt = delete(likes).where((likes.c.user_id == current_user.id) & (likes.c.book_id == book_id))
        result = await db.execute(delete_stmt)

        if result.rowcount == 0:
            logger.warning(f"Пользователь {current_user.id} пытается убрать несуществующий лайк с книги {book_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Лайк не найден. Возможно, вы не лайкали эту книгу."
            )

        await db.commit()

        logger.info(f"Пользователь {current_user.id} убрал лайк с книги {book_id}")
        return {"message": "Лайк успешно удален"}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при удалении лайка: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера")


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
        # Запрос для получения книг, которые лайкнул пользователь
        query = (
            select(Book)
            .join(likes, Book.id == likes.c.book_id)
            .where(likes.c.user_id == current_user.id)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
        )

        result = await db.execute(query)
        books = result.scalars().all()

        logger.info(f"Получено {len(books)} лайкнутых книг пользователя {current_user.id}")

        # Преобразуем книги в модели Pydantic
        return [BookResponse.model_validate(book) for book in books]

    except Exception as e:
        logger.error(f"Ошибка при получении лайкнутых книг: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера")
