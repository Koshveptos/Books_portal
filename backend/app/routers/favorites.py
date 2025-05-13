from typing import List

from auth import current_active_user
from core.database import get_db
from core.logger_config import logger
from fastapi import APIRouter, Depends, HTTPException, status
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
        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            logger.warning(
                f"Попытка добавить в избранное несуществующую книгу: id={book_id}, пользователь id={current_user.id}"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")

        # Проверяем, есть ли уже эта книга в избранном
        favorite_query = select(favorites).where(
            (favorites.c.user_id == current_user.id) & (favorites.c.book_id == book_id)
        )
        result = await db.execute(favorite_query)
        existing_favorite = result.first()

        if existing_favorite:
            logger.info(f"Книга {book_id} уже в избранном пользователя {current_user.id}")
            return {"message": "Книга уже в избранном"}

        # Добавляем в избранное
        insert_stmt = insert(favorites).values(user_id=current_user.id, book_id=book_id)
        await db.execute(insert_stmt)
        await db.commit()

        logger.info(f"Пользователь {current_user.id} добавил книгу {book_id} в избранное")
        return {"message": "Книга добавлена в избранное"}

    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Ошибка целостности при добавлении в избранное: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ошибка при добавлении в избранное")
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при добавлении в избранное: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера")


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
        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        result = await db.execute(book_query)
        book = result.scalar_one_or_none()

        if not book:
            logger.warning(
                f"Попытка удалить из избранного несуществующую книгу: id={book_id}, пользователь id={current_user.id}"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")

        # Удаляем из избранного
        delete_stmt = delete(favorites).where(
            (favorites.c.user_id == current_user.id) & (favorites.c.book_id == book_id)
        )
        result = await db.execute(delete_stmt)

        if result.rowcount == 0:
            logger.warning(
                f"Пользователь {current_user.id} пытается удалить из избранного книгу {book_id}, которой там нет"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена в избранном")

        await db.commit()

        logger.info(f"Пользователь {current_user.id} удалил книгу {book_id} из избранного")
        return {"message": "Книга удалена из избранного"}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при удалении из избранного: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера")


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
        # Запрос для получения книг из избранного пользователя
        query = (
            select(Book)
            .join(favorites, Book.id == favorites.c.book_id)
            .where(favorites.c.user_id == current_user.id)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
        )

        result = await db.execute(query)
        books = result.scalars().all()

        logger.info(f"Получено {len(books)} избранных книг пользователя {current_user.id}")

        # Преобразуем книги в модели Pydantic
        return [BookResponse.model_validate(book) for book in books]

    except Exception as e:
        logger.error(f"Ошибка при получении избранных книг: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера")
