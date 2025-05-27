from typing import Dict, List, Optional

from models.book import Author, Book, Category, Rating, Tag, favorites, likes
from schemas.book import BookCreate, BookUpdate
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class BookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_book(self, book_id: int, user_id: Optional[int] = None) -> Optional[Book]:
        """
        Получить книгу по ID с информацией о лайках и избранном.

        Args:
            book_id: ID книги
            user_id: ID пользователя (опционально)
        """
        query = (
            select(Book)
            .options(
                selectinload(Book.authors),
                selectinload(Book.categories),
                selectinload(Book.tags),
                selectinload(Book.ratings),
            )
            .where(Book.id == book_id)
        )

        result = await self.db.execute(query)
        book = result.scalar_one_or_none()

        if book and user_id:
            # Получаем информацию о лайках и избранном
            likes_count = await self.db.execute(
                select(func.count()).select_from(likes).where(likes.c.book_id == book_id)
            )
            favorites_count = await self.db.execute(
                select(func.count()).select_from(favorites).where(favorites.c.book_id == book_id)
            )

            # Проверяем, лайкнул ли и добавил ли в избранное текущий пользователь
            is_liked = await self.db.execute(
                select(likes).where(and_(likes.c.book_id == book_id, likes.c.user_id == user_id))
            )
            is_favorited = await self.db.execute(
                select(favorites).where(and_(favorites.c.book_id == book_id, favorites.c.user_id == user_id))
            )

            book.likes_count = likes_count.scalar() or 0
            book.favorites_count = favorites_count.scalar() or 0
            book.is_liked = bool(is_liked.scalar_one_or_none())
            book.is_favorited = bool(is_favorited.scalar_one_or_none())

        return book

    async def get_books(
        self,
        skip: int = 0,
        limit: int = 10,
        user_id: Optional[int] = None,
        search: Optional[str] = None,
        author_id: Optional[int] = None,
        category_id: Optional[int] = None,
        tag_id: Optional[int] = None,
        min_rating: Optional[float] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        sort_by: str = "rating",
        sort_order: str = "desc",
    ) -> List[Book]:
        """
        Получить список книг с фильтрацией и сортировкой.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей
            user_id: ID пользователя (опционально)
            search: Поисковый запрос
            author_id: ID автора для фильтрации
            category_id: ID категории для фильтрации
            tag_id: ID тега для фильтрации
            min_rating: Минимальный рейтинг
            min_year: Минимальный год издания
            max_year: Максимальный год издания
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc/desc)
        """
        # Базовый запрос с подзапросом для среднего рейтинга
        avg_rating_subq = (
            select(func.avg(Rating.rating).label("avg_rating")).where(Rating.book_id == Book.id).scalar_subquery()
        )

        query = select(Book, avg_rating_subq.label("avg_rating")).options(
            selectinload(Book.authors),
            selectinload(Book.categories),
            selectinload(Book.tags),
            selectinload(Book.ratings),
        )

        # Применяем фильтры
        if search:
            search_condition = or_(Book.title.ilike(f"%{search}%"), Book.description.ilike(f"%{search}%"))
            query = query.where(search_condition)

        if author_id:
            query = query.join(Book.authors).where(Author.id == author_id)

        if category_id:
            query = query.join(Book.categories).where(Category.id == category_id)

        if tag_id:
            query = query.join(Book.tags).where(Tag.id == tag_id)

        if min_rating is not None:
            query = query.having(avg_rating_subq >= min_rating)

        if min_year is not None:
            query = query.where(Book.year >= min_year)

        if max_year is not None:
            query = query.where(Book.year <= max_year)

        # Применяем сортировку
        if sort_by == "rating":
            sort_column = avg_rating_subq
        elif sort_by == "year":
            sort_column = Book.year
        elif sort_by == "title":
            sort_column = Book.title
        else:
            sort_column = avg_rating_subq

        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Применяем пагинацию
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        books_with_ratings = result.all()

        # Преобразуем результаты
        books = []
        for book, avg_rating in books_with_ratings:
            book.rating_book = avg_rating or 0.0
            books.append(book)

        if user_id:
            # Получаем информацию о лайках и избранном для всех книг
            for book in books:
                likes_count = await self.db.execute(
                    select(func.count()).select_from(likes).where(likes.c.book_id == book.id)
                )
                favorites_count = await self.db.execute(
                    select(func.count()).select_from(favorites).where(favorites.c.book_id == book.id)
                )

                is_liked = await self.db.execute(
                    select(likes).where(and_(likes.c.book_id == book.id, likes.c.user_id == user_id))
                )
                is_favorited = await self.db.execute(
                    select(favorites).where(and_(favorites.c.book_id == book.id, favorites.c.user_id == user_id))
                )

                book.likes_count = likes_count.scalar() or 0
                book.favorites_count = favorites_count.scalar() or 0
                book.is_liked = bool(is_liked.scalar_one_or_none())
                book.is_favorited = bool(is_favorited.scalar_one_or_none())

        return books

    async def create_book(self, book_data: BookCreate) -> Book:
        """
        Создать новую книгу.

        Args:
            book_data: Данные для создания книги
        """
        try:
            # Создаем новую книгу
            book = Book(
                title=book_data.title,
                description=book_data.description,
                year=book_data.year,
                publisher=book_data.publisher,
                isbn=book_data.isbn,
                cover_url=book_data.cover_url,
                language=book_data.language,
                file_url=book_data.file_url,
            )

            # Получаем авторов
            if book_data.author_ids:
                authors_query = select(Author).where(Author.id.in_(book_data.author_ids))
                authors_result = await self.db.execute(authors_query)
                book.authors = authors_result.scalars().all()

            # Получаем категории
            if book_data.category_ids:
                categories_query = select(Category).where(Category.id.in_(book_data.category_ids))
                categories_result = await self.db.execute(categories_query)
                book.categories = categories_result.scalars().all()

            # Получаем теги
            if book_data.tag_ids:
                tags_query = select(Tag).where(Tag.id.in_(book_data.tag_ids))
                tags_result = await self.db.execute(tags_query)
                book.tags = tags_result.scalars().all()

            # Сохраняем книгу в базе данных
            self.db.add(book)
            await self.db.commit()
            await self.db.refresh(book)

            return book
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при создании книги: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise

    async def update_book(self, book_id: int, book_data: BookUpdate) -> Optional[Book]:
        """
        Обновить информацию о книге.

        Args:
            book_id: ID книги
            book_data: Данные для обновления
        """
        try:
            # Получаем книгу
            book = await self.get_book(book_id)
            if not book:
                return None

            # Обновляем основные поля
            fields_to_update = {
                k: v
                for k, v in book_data.model_dump(exclude_unset=True).items()
                if k not in ["author_ids", "category_ids", "tag_ids"]
            }

            for field, value in fields_to_update.items():
                setattr(book, field, value)

            # Обновляем авторов
            if book_data.author_ids is not None:
                authors_query = select(Author).where(Author.id.in_(book_data.author_ids))
                authors_result = await self.db.execute(authors_query)
                book.authors = authors_result.scalars().all()

            # Обновляем категории
            if book_data.category_ids is not None:
                categories_query = select(Category).where(Category.id.in_(book_data.category_ids))
                categories_result = await self.db.execute(categories_query)
                book.categories = categories_result.scalars().all()

            # Обновляем теги
            if book_data.tag_ids is not None:
                tags_query = select(Tag).where(Tag.id.in_(book_data.tag_ids))
                tags_result = await self.db.execute(tags_query)
                book.tags = tags_result.scalars().all()

            # Сохраняем изменения
            await self.db.commit()
            await self.db.refresh(book)

            return book
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при обновлении книги: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise

    async def delete_book(self, book_id: int) -> bool:
        """
        Удалить книгу.

        Args:
            book_id: ID книги
        """
        book = await self.get_book(book_id)
        if not book:
            return False

        await self.db.delete(book)
        await self.db.commit()
        return True

    async def get_popular_books(
        self, limit: int = 10, user_id: Optional[int] = None, min_ratings_count: int = 5
    ) -> List[Book]:
        """
        Получить список популярных книг.

        Args:
            limit: Максимальное количество книг
            user_id: ID пользователя (опционально)
            min_ratings_count: Минимальное количество оценок
        """
        query = (
            select(Book)
            .options(
                selectinload(Book.authors),
                selectinload(Book.categories),
                selectinload(Book.tags),
                selectinload(Book.ratings),
            )
            .join(Rating)
            .group_by(Book.id)
            .having(func.count(Rating.id) >= min_ratings_count)
            .order_by(desc(Book.rating_book))
            .limit(limit)
        )

        result = await self.db.execute(query)
        books = result.scalars().all()

        if user_id:
            # Получаем информацию о лайках и избранном
            for book in books:
                likes_count = await self.db.execute(
                    select(func.count()).select_from(likes).where(likes.c.book_id == book.id)
                )
                favorites_count = await self.db.execute(
                    select(func.count()).select_from(favorites).where(favorites.c.book_id == book.id)
                )

                is_liked = await self.db.execute(
                    select(likes).where(and_(likes.c.book_id == book.id, likes.c.user_id == user_id))
                )
                is_favorited = await self.db.execute(
                    select(favorites).where(and_(favorites.c.book_id == book.id, favorites.c.user_id == user_id))
                )

                book.likes_count = likes_count.scalar() or 0
                book.favorites_count = favorites_count.scalar() or 0
                book.is_liked = bool(is_liked.scalar_one_or_none())
                book.is_favorited = bool(is_favorited.scalar_one_or_none())

        return books

    async def _get_user_ratings(self, user_id: int) -> Dict[int, float]:
        """
        Получить словарь {book_id: rating} для оценок пользователя.

        Args:
            user_id: ID пользователя
        """
        query = select(Rating.book_id, Rating.rating).where(Rating.user_id == user_id)
        result = await self.db.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def search_books(
        self, query: str, limit: int = 10, min_ratings_count: int = 5, user_id: Optional[int] = None
    ) -> List[Book]:
        """
        Поиск книг по запросу.

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            min_ratings_count: Минимальное количество оценок
            user_id: ID пользователя (опционально)
        """
        import logging

        logger = logging.getLogger(__name__)

        # Инициализируем пустой список для результатов
        results = []

        try:
            # Проверяем входные параметры
            if not query or len(query.strip()) < 3:
                logger.info(f"Поисковый запрос слишком короткий: '{query}'")
                return []

            clean_query = query.strip().lower()
            logger.info(f"Поиск книг по запросу: '{clean_query}'")

            # Готовим общие опции для обоих запросов
            load_options = [
                selectinload(Book.authors),
                selectinload(Book.categories),
                selectinload(Book.tags),
                selectinload(Book.ratings),
            ]

            # 1. Ищем книги по названию и описанию
            try:
                # Формируем условие поиска по названию и описанию
                title_desc_condition = or_(
                    Book.title.ilike(f"%{clean_query}%"), Book.description.ilike(f"%{clean_query}%")
                )

                title_desc_query = select(Book).options(*load_options).where(title_desc_condition)

                if min_ratings_count > 0:
                    # Создаем подзапрос для подсчета оценок
                    ratings_count_subq = (
                        select(func.count(Rating.id)).where(Rating.book_id == Book.id).scalar_subquery()
                    )
                    title_desc_query = title_desc_query.where(ratings_count_subq >= min_ratings_count)

                # Выполняем запрос с сортировкой по рейтингу
                result = await self.db.execute(title_desc_query.order_by(desc(Book.rating_book)).limit(limit))
                title_desc_books = list(result.scalars().all())
                logger.info(f"Найдено {len(title_desc_books)} книг по названию и описанию")

                # Добавляем результаты в общий список
                results.extend(title_desc_books)
            except Exception as e:
                logger.error(f"Ошибка при поиске по названию и описанию: {str(e)}", exc_info=True)

            # 2. Ищем книги по авторам, если результаты еще не достигли лимита
            if len(results) < limit:
                try:
                    author_query = (
                        select(Book)
                        .join(Book.authors)
                        .options(*load_options)
                        .where(Author.name.ilike(f"%{clean_query}%"))
                    )

                    if min_ratings_count > 0:
                        # Создаем подзапрос для подсчета оценок
                        ratings_count_subq = (
                            select(func.count(Rating.id)).where(Rating.book_id == Book.id).scalar_subquery()
                        )
                        author_query = author_query.where(ratings_count_subq >= min_ratings_count)

                    # Выполняем запрос с сортировкой по рейтингу
                    result = await self.db.execute(
                        author_query.order_by(desc(Book.rating_book)).limit(limit - len(results))
                    )
                    author_books = list(result.scalars().all())
                    logger.info(f"Найдено {len(author_books)} книг по авторам")

                    # Добавляем только уникальные результаты
                    book_ids = {book.id for book in results}
                    for book in author_books:
                        if book.id not in book_ids:
                            results.append(book)
                            book_ids.add(book.id)
                except Exception as e:
                    logger.error(f"Ошибка при поиске по авторам: {str(e)}", exc_info=True)

            # Сортируем объединенные результаты
            results = sorted(results, key=lambda book: book.rating_book if book.rating_book else 0, reverse=True)[
                :limit
            ]
            logger.info(f"Итоговое количество найденных книг: {len(results)}")

            # Добавляем информацию о лайках и избранном, если указан user_id
            if user_id and results:
                await self._add_user_interaction_info(results, user_id)

            return results

        except Exception as e:
            logger.error(f"Критическая ошибка в search_books: {str(e)}", exc_info=True)
            return []

    async def _add_user_interaction_info(self, books: List[Book], user_id: int) -> None:
        """
        Добавляет информацию о лайках и избранном для списка книг.

        Args:
            books: Список книг
            user_id: ID пользователя
        """
        if not books or not user_id:
            return

        try:
            # Получаем все ID книг
            book_ids = [book.id for book in books]

            # Запрос на получение лайков
            likes_query = select(likes.c.book_id).where(and_(likes.c.book_id.in_(book_ids), likes.c.user_id == user_id))
            likes_result = await self.db.execute(likes_query)
            liked_book_ids = {row[0] for row in likes_result.all()}

            # Запрос на получение избранного
            favorites_query = select(favorites.c.book_id).where(
                and_(favorites.c.book_id.in_(book_ids), favorites.c.user_id == user_id)
            )
            favorites_result = await self.db.execute(favorites_query)
            favorited_book_ids = {row[0] for row in favorites_result.all()}

            # Запрос на получение количества лайков
            likes_count_query = (
                select(likes.c.book_id, func.count(likes.c.user_id).label("count"))
                .where(likes.c.book_id.in_(book_ids))
                .group_by(likes.c.book_id)
            )
            likes_count_result = await self.db.execute(likes_count_query)
            likes_counts = {row[0]: row[1] for row in likes_count_result.all()}

            # Запрос на получение количества избранного
            favorites_count_query = (
                select(favorites.c.book_id, func.count(favorites.c.user_id).label("count"))
                .where(favorites.c.book_id.in_(book_ids))
                .group_by(favorites.c.book_id)
            )
            favorites_count_result = await self.db.execute(favorites_count_query)
            favorites_counts = {row[0]: row[1] for row in favorites_count_result.all()}

            # Устанавливаем информацию для каждой книги
            for book in books:
                book.likes_count = likes_counts.get(book.id, 0)
                book.favorites_count = favorites_counts.get(book.id, 0)
                book.is_liked = book.id in liked_book_ids
                book.is_favorited = book.id in favorited_book_ids

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при добавлении информации о взаимодействиях: {str(e)}", exc_info=True)

    async def search_books_by_category(
        self, category_id: int, limit: int = 10, user_id: Optional[int] = None
    ) -> List[Book]:
        """
        Поиск книг по категории.

        Args:
            category_id: ID категории
            limit: Максимальное количество результатов
            user_id: ID пользователя (опционально)

        Returns:
            Список книг, относящихся к указанной категории
        """
        # Подзапрос для среднего рейтинга
        avg_rating_subq = (
            select(func.avg(Rating.rating).label("avg_rating")).where(Rating.book_id == Book.id).scalar_subquery()
        )

        query = (
            select(Book, avg_rating_subq.label("avg_rating"))
            .join(Book.categories)
            .where(Category.id == category_id)
            .options(
                selectinload(Book.authors),
                selectinload(Book.categories),
                selectinload(Book.tags),
                selectinload(Book.ratings),
            )
            .order_by(desc(avg_rating_subq))
            .limit(limit)
        )

        result = await self.db.execute(query)
        books_with_ratings = result.all()

        # Преобразуем результаты
        books = []
        for book, avg_rating in books_with_ratings:
            book.rating_book = avg_rating or 0.0
            books.append(book)

        # Добавляем информацию о лайках и избранном, если указан user_id
        if user_id:
            for book in books:
                likes_count = await self.db.execute(
                    select(func.count()).select_from(likes).where(likes.c.book_id == book.id)
                )
                favorites_count = await self.db.execute(
                    select(func.count()).select_from(favorites).where(favorites.c.book_id == book.id)
                )

                is_liked = await self.db.execute(
                    select(likes).where(and_(likes.c.book_id == book.id, likes.c.user_id == user_id))
                )
                is_favorited = await self.db.execute(
                    select(favorites).where(and_(favorites.c.book_id == book.id, favorites.c.user_id == user_id))
                )

                book.likes_count = likes_count.scalar() or 0
                book.favorites_count = favorites_count.scalar() or 0
                book.is_liked = bool(is_liked.scalar_one_or_none())
                book.is_favorited = bool(is_favorited.scalar_one_or_none())

        return books

    async def search_books_by_tag(self, tag_id: int, limit: int = 10, user_id: Optional[int] = None) -> List[Book]:
        """
        Поиск книг по тегу.

        Args:
            tag_id: ID тега
            limit: Максимальное количество результатов
            user_id: ID пользователя (опционально)

        Returns:
            Список книг, отмеченных указанным тегом
        """
        query = (
            select(Book)
            .join(Book.tags)
            .where(Tag.id == tag_id)
            .options(
                selectinload(Book.authors),
                selectinload(Book.categories),
                selectinload(Book.tags),
                selectinload(Book.ratings),
            )
            .order_by(desc(Book.rating_book))
            .limit(limit)
        )

        result = await self.db.execute(query)
        books = list(result.scalars().all())

        # Добавляем информацию о лайках и избранном, если указан user_id
        if user_id:
            for book in books:
                likes_count = await self.db.execute(
                    select(func.count()).select_from(likes).where(likes.c.book_id == book.id)
                )
                favorites_count = await self.db.execute(
                    select(func.count()).select_from(favorites).where(favorites.c.book_id == book.id)
                )

                is_liked = await self.db.execute(
                    select(likes).where(and_(likes.c.book_id == book.id, likes.c.user_id == user_id))
                )
                is_favorited = await self.db.execute(
                    select(favorites).where(and_(favorites.c.book_id == book.id, favorites.c.user_id == user_id))
                )

                book.likes_count = likes_count.scalar() or 0
                book.favorites_count = favorites_count.scalar() or 0
                book.is_liked = bool(is_liked.scalar_one_or_none())
                book.is_favorited = bool(is_favorited.scalar_one_or_none())

        return books

    async def get_user_likes(self, user_id: int, limit: int = 10, skip: int = 0) -> List[Book]:
        """
        Получить список книг, которые понравились пользователю.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество результатов
            skip: Количество пропускаемых записей

        Returns:
            Список книг, которые понравились пользователю
        """
        # Подзапрос для среднего рейтинга
        avg_rating_subq = (
            select(func.avg(Rating.rating).label("avg_rating")).where(Rating.book_id == Book.id).scalar_subquery()
        )

        query = (
            select(Book, avg_rating_subq.label("avg_rating"))
            .join(likes, Book.id == likes.c.book_id)
            .where(likes.c.user_id == user_id)
            .options(
                selectinload(Book.authors),
                selectinload(Book.categories),
                selectinload(Book.tags),
                selectinload(Book.ratings),
            )
            .order_by(desc(avg_rating_subq))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        books_with_ratings = result.all()

        # Преобразуем результаты
        books = []
        for book, avg_rating in books_with_ratings:
            book.rating_book = avg_rating or 0.0
            book.is_liked = True
            books.append(book)

        # Добавляем информацию о лайках и избранном
        for book in books:
            likes_count = await self.db.execute(
                select(func.count()).select_from(likes).where(likes.c.book_id == book.id)
            )
            favorites_count = await self.db.execute(
                select(func.count()).select_from(favorites).where(favorites.c.book_id == book.id)
            )
            is_favorited = await self.db.execute(
                select(favorites).where(and_(favorites.c.book_id == book.id, favorites.c.user_id == user_id))
            )

            book.likes_count = likes_count.scalar() or 0
            book.favorites_count = favorites_count.scalar() or 0
            book.is_favorited = bool(is_favorited.scalar_one_or_none())

        return books

    async def get_user_favorites(self, user_id: int, limit: int = 10, skip: int = 0) -> List[Book]:
        """
        Получить список книг в избранном пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество результатов
            skip: Количество пропускаемых записей

        Returns:
            Список книг в избранном пользователя
        """
        # Подзапрос для среднего рейтинга
        avg_rating_subq = (
            select(func.avg(Rating.rating).label("avg_rating")).where(Rating.book_id == Book.id).scalar_subquery()
        )

        query = (
            select(Book, avg_rating_subq.label("avg_rating"))
            .join(favorites, Book.id == favorites.c.book_id)
            .where(favorites.c.user_id == user_id)
            .options(
                selectinload(Book.authors),
                selectinload(Book.categories),
                selectinload(Book.tags),
                selectinload(Book.ratings),
            )
            .order_by(desc(avg_rating_subq))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        books_with_ratings = result.all()

        # Преобразуем результаты
        books = []
        for book, avg_rating in books_with_ratings:
            book.rating_book = avg_rating or 0.0
            book.is_favorited = True
            books.append(book)

        # Добавляем информацию о лайках и избранном
        for book in books:
            likes_count = await self.db.execute(
                select(func.count()).select_from(likes).where(likes.c.book_id == book.id)
            )
            favorites_count = await self.db.execute(
                select(func.count()).select_from(favorites).where(favorites.c.book_id == book.id)
            )
            is_liked = await self.db.execute(
                select(likes).where(and_(likes.c.book_id == book.id, likes.c.user_id == user_id))
            )

            book.likes_count = likes_count.scalar() or 0
            book.favorites_count = favorites_count.scalar() or 0
            book.is_liked = bool(is_liked.scalar_one_or_none())

        return books

    async def get_user_ratings(self, user_id: int, limit: int = 10, skip: int = 0) -> List[tuple[Book, float]]:
        """
        Получить список книг с оценками пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество результатов
            skip: Количество пропускаемых записей

        Returns:
            Список кортежей (книга, оценка пользователя)
        """
        query = (
            select(Book, Rating.rating)
            .join(Rating, Book.id == Rating.book_id)
            .where(Rating.user_id == user_id)
            .options(
                selectinload(Book.authors),
                selectinload(Book.categories),
                selectinload(Book.tags),
                selectinload(Book.ratings),
            )
            .order_by(desc(Rating.rating))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        books_with_ratings = result.all()

        # Преобразуем результаты
        books = []
        for book, user_rating in books_with_ratings:
            # Вычисляем средний рейтинг
            avg_rating_query = select(func.avg(Rating.rating)).where(Rating.book_id == book.id)
            avg_rating_result = await self.db.execute(avg_rating_query)
            avg_rating = avg_rating_result.scalar() or 0.0

            book.rating_book = avg_rating
            books.append((book, user_rating))

        # Добавляем информацию о лайках и избранном
        for book, _ in books:
            likes_count = await self.db.execute(
                select(func.count()).select_from(likes).where(likes.c.book_id == book.id)
            )
            favorites_count = await self.db.execute(
                select(func.count()).select_from(favorites).where(favorites.c.book_id == book.id)
            )
            is_liked = await self.db.execute(
                select(likes).where(and_(likes.c.book_id == book.id, likes.c.user_id == user_id))
            )
            is_favorited = await self.db.execute(
                select(favorites).where(and_(favorites.c.book_id == book.id, favorites.c.user_id == user_id))
            )

            book.likes_count = likes_count.scalar() or 0
            book.favorites_count = favorites_count.scalar() or 0
            book.is_liked = bool(is_liked.scalar_one_or_none())
            book.is_favorited = bool(is_favorited.scalar_one_or_none())

        return books
