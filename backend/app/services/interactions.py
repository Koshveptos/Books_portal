from typing import List, Optional

from models.book import Book, Rating, favorites, likes
from schemas.interactions import RatingCreate
from sqlalchemy import and_, delete, desc, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload


class InteractionsService:
    """Сервис для работы с взаимодействиями пользователей с книгами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_rating(self, user_id: int, rating_data: RatingCreate) -> Rating:
        """
        Создать или обновить оценку книги.

        Args:
            user_id: ID пользователя
            rating_data: Данные оценки
        """
        # Проверяем существование книги
        book_id = rating_data.book_id
        book_query = select(Book).where(Book.id == book_id)
        book_result = await self.db.execute(book_query)
        book = book_result.scalar_one_or_none()

        if not book:
            raise ValueError(f"Книга с ID {book_id} не найдена")

        # Проверяем, есть ли уже оценка от этого пользователя
        query = select(Rating).where(and_(Rating.user_id == user_id, Rating.book_id == book_id))
        result = await self.db.execute(query)
        existing_rating = result.scalar_one_or_none()

        if existing_rating:
            # Обновляем существующую оценку
            existing_rating.rating = rating_data.rating
            existing_rating.comment = rating_data.comment
            self.db.add(existing_rating)
            await self.db.commit()
            await self.db.refresh(existing_rating)
            return existing_rating
        else:
            # Создаем новую оценку
            rating = Rating(user_id=user_id, book_id=book_id, rating=rating_data.rating, comment=rating_data.comment)
            self.db.add(rating)
            await self.db.commit()
            await self.db.refresh(rating)
            return rating

    async def get_user_ratings(
        self, user_id: int, book_id: Optional[int] = None, skip: int = 0, limit: int = 10
    ) -> List[Rating]:
        """
        Получить оценки пользователя.

        Args:
            user_id: ID пользователя
            book_id: ID книги (опционально)
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей
        """
        query = (
            select(Rating)
            .where(Rating.user_id == user_id)
            .options(joinedload(Rating.book))
            .order_by(desc(Rating.created_at))
            .offset(skip)
            .limit(limit)
        )

        if book_id:
            query = query.where(Rating.book_id == book_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_book_ratings(self, book_id: int, skip: int = 0, limit: int = 10) -> List[Rating]:
        """
        Получить оценки книги.

        Args:
            book_id: ID книги
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей
        """
        query = (
            select(Rating)
            .where(Rating.book_id == book_id)
            .options(joinedload(Rating.user))
            .order_by(desc(Rating.created_at))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_rating(self, rating_id: int, user_id: int) -> bool:
        """
        Удалить оценку.

        Args:
            rating_id: ID оценки
            user_id: ID пользователя (для проверки владения)
        """
        # Находим оценку и проверяем владельца
        query = select(Rating).where(and_(Rating.id == rating_id, Rating.user_id == user_id))
        result = await self.db.execute(query)
        rating = result.scalar_one_or_none()

        if not rating:
            return False

        # Удаляем оценку
        await self.db.delete(rating)
        await self.db.commit()
        return True

    async def like_book(self, user_id: int, book_id: int) -> bool:
        """
        Поставить лайк книге.

        Args:
            user_id: ID пользователя
            book_id: ID книги
        """
        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        book_result = await self.db.execute(book_query)
        book = book_result.scalar_one_or_none()

        if not book:
            raise ValueError(f"Книга с ID {book_id} не найдена")

        # Проверяем, есть ли уже лайк
        query = select(likes).where(and_(likes.c.user_id == user_id, likes.c.book_id == book_id))
        result = await self.db.execute(query)
        existing_like = result.scalar_one_or_none()

        if existing_like:
            # Лайк уже существует
            return True

        # Добавляем лайк
        stmt = insert(likes).values(user_id=user_id, book_id=book_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def unlike_book(self, user_id: int, book_id: int) -> bool:
        """
        Убрать лайк с книги.

        Args:
            user_id: ID пользователя
            book_id: ID книги
        """
        # Удаляем лайк
        stmt = delete(likes).where(and_(likes.c.user_id == user_id, likes.c.book_id == book_id))
        await self.db.execute(stmt)
        await self.db.commit()

        # Возвращаем True, даже если лайк не был найден
        return True

    async def add_to_favorites(self, user_id: int, book_id: int) -> bool:
        """
        Добавить книгу в избранное.

        Args:
            user_id: ID пользователя
            book_id: ID книги
        """
        # Проверяем существование книги
        book_query = select(Book).where(Book.id == book_id)
        book_result = await self.db.execute(book_query)
        book = book_result.scalar_one_or_none()

        if not book:
            raise ValueError(f"Книга с ID {book_id} не найдена")

        # Проверяем, есть ли уже в избранном
        query = select(favorites).where(and_(favorites.c.user_id == user_id, favorites.c.book_id == book_id))
        result = await self.db.execute(query)
        existing_favorite = result.scalar_one_or_none()

        if existing_favorite:
            # Книга уже в избранном
            return True

        # Добавляем в избранное
        stmt = insert(favorites).values(user_id=user_id, book_id=book_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def remove_from_favorites(self, user_id: int, book_id: int) -> bool:
        """
        Удалить книгу из избранного.

        Args:
            user_id: ID пользователя
            book_id: ID книги
        """
        # Удаляем из избранного
        stmt = delete(favorites).where(and_(favorites.c.user_id == user_id, favorites.c.book_id == book_id))
        await self.db.execute(stmt)
        await self.db.commit()

        # Возвращаем True, даже если запись не была найдена
        return True

    async def get_user_likes(self, user_id: int) -> List[Book]:
        """
        Получить список книг, которые лайкнул пользователь.

        Args:
            user_id: ID пользователя
        """
        query = (
            select(Book)
            .join(likes, Book.id == likes.c.book_id)
            .where(likes.c.user_id == user_id)
            .options(selectinload(Book.author), selectinload(Book.category), selectinload(Book.tags))
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user_favorites(self, user_id: int) -> List[Book]:
        """
        Получить список избранных книг пользователя.

        Args:
            user_id: ID пользователя
        """
        query = (
            select(Book)
            .join(favorites, Book.id == favorites.c.book_id)
            .where(favorites.c.user_id == user_id)
            .options(selectinload(Book.author), selectinload(Book.category), selectinload(Book.tags))
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def is_book_liked(self, user_id: int, book_id: int) -> bool:
        """
        Проверить, лайкнул ли пользователь книгу.

        Args:
            user_id: ID пользователя
            book_id: ID книги
        """
        query = select(likes).where(and_(likes.c.user_id == user_id, likes.c.book_id == book_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def is_book_favorited(self, user_id: int, book_id: int) -> bool:
        """
        Проверить, добавил ли пользователь книгу в избранное.

        Args:
            user_id: ID пользователя
            book_id: ID книги
        """
        query = select(favorites).where(and_(favorites.c.user_id == user_id, favorites.c.book_id == book_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
