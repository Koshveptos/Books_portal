from typing import List, Optional

from core.logger_config import logger
from models.book import Author, Book, book_authors, books_categories, books_tags
from schemas.book import (
    BookCreate,
    BookPartial,
    BookUpdate,
)
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class BooksService:
    """Service for managing books in the system."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_books(self, skip: int = 0, limit: int = 100) -> List[Book]:
        """
        Get all books with pagination.

        Args:
            skip: Number of books to skip
            limit: Maximum number of books to return

        Returns:
            List of books
        """
        query = (
            select(Book)
            .options(selectinload(Book.categories), selectinload(Book.tags), selectinload(Book.authors))
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        books = list(result.scalars().all())
        logger.info(f"Retrieved {len(books)} books (skip={skip}, limit={limit})")
        return books

    async def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """
        Get book by ID with all relationships loaded.

        Args:
            book_id: Book identifier

        Returns:
            Book object or None if not found
        """
        query = (
            select(Book)
            .where(Book.id == book_id)
            .options(selectinload(Book.categories), selectinload(Book.tags), selectinload(Book.authors))
        )

        result = await self.session.execute(query)
        book = result.scalars().first()

        if book:
            logger.info(f"Retrieved book: '{book.title}' (ID: {book.id})")
        else:
            logger.warning(f"Book with ID {book_id} not found")

        return book

    async def get_book_by_title(self, title: str) -> Optional[Book]:
        """
        Get book by title.

        Args:
            title: Book title

        Returns:
            Book object or None if not found
        """
        query = select(Book).where(Book.title == title)
        result = await self.session.execute(query)
        book = result.scalars().first()

        if book:
            logger.info(f"Retrieved book by title: '{title}' (ID: {book.id})")

        return book

    async def create_book(self, book_data: BookCreate) -> Book:
        """
        Create a new book with associated relationships.

        Args:
            book_data: Book creation data including categories, tags, and authors

        Returns:
            Created book object

        Raises:
            ValueError: If book with the same title already exists
        """
        # Check if book with same title already exists
        existing_book = await self.get_book_by_title(book_data.title)
        if existing_book:
            error_msg = f"Book with title '{book_data.title}' already exists"
            logger.warning(error_msg)
            raise ValueError(error_msg)

        # Create book object
        book_dict = book_data.model_dump(exclude={"categories", "tags", "authors"})
        db_book = Book(**book_dict)

        self.session.add(db_book)
        await self.session.flush()

        # Add categories
        if book_data.categories:
            for category_id in book_data.categories:
                stmt = books_categories.insert().values(book_id=db_book.id, category_id=category_id)
                await self.session.execute(stmt)

        # Add tags
        if book_data.tags:
            for tag_id in book_data.tags:
                stmt = books_tags.insert().values(book_id=db_book.id, tag_id=tag_id)
                await self.session.execute(stmt)

        # Add authors
        if book_data.authors:
            for author_id in book_data.authors:
                stmt = book_authors.insert().values(book_id=db_book.id, author_id=author_id)
                await self.session.execute(stmt)

        await self.session.commit()

        # Reload the book with all relationships
        db_book = await self.get_book_by_id(db_book.id)

        logger.info(f"Book created: '{db_book.title}' (ID: {db_book.id})")
        return db_book

    async def update_book(self, book_id: int, book_data: BookUpdate) -> Optional[Book]:
        """
        Update book information completely.

        Args:
            book_id: Book identifier
            book_data: Book update data

        Returns:
            Updated book or None if not found

        Raises:
            ValueError: If book with the same title already exists
        """
        # Get book by ID
        book = await self.get_book_by_id(book_id)
        if not book:
            return None

        # Check title uniqueness if it's changed
        if book_data.title != book.title:
            existing_book = await self.get_book_by_title(book_data.title)
            if existing_book and existing_book.id != book_id:
                error_msg = f"Book with title '{book_data.title}' already exists"
                logger.warning(error_msg)
                raise ValueError(error_msg)

        # Update basic fields
        book_dict = book_data.model_dump(exclude={"categories", "tags", "authors"})
        for key, value in book_dict.items():
            setattr(book, key, value)

        # Update categories - clear and recreate
        stmt = books_categories.delete().where(books_categories.c.book_id == book_id)
        await self.session.execute(stmt)

        if book_data.categories:
            for category_id in book_data.categories:
                stmt = books_categories.insert().values(book_id=book_id, category_id=category_id)
                await self.session.execute(stmt)

        # Update tags - clear and recreate
        stmt = books_tags.delete().where(books_tags.c.book_id == book_id)
        await self.session.execute(stmt)

        if book_data.tags:
            for tag_id in book_data.tags:
                stmt = books_tags.insert().values(book_id=book_id, tag_id=tag_id)
                await self.session.execute(stmt)

        # Update authors - clear and recreate
        stmt = book_authors.delete().where(book_authors.c.book_id == book_id)
        await self.session.execute(stmt)

        if book_data.authors:
            for author_id in book_data.authors:
                stmt = book_authors.insert().values(book_id=book_id, author_id=author_id)
                await self.session.execute(stmt)

        await self.session.commit()

        # Reload the book with all relationships
        updated_book = await self.get_book_by_id(book_id)

        logger.info(f"Book updated: '{updated_book.title}' (ID: {updated_book.id})")
        return updated_book

    async def partial_update_book(self, book_id: int, book_data: BookPartial) -> Optional[Book]:
        """
        Update book information partially.

        Args:
            book_id: Book identifier
            book_data: Partial book update data

        Returns:
            Updated book or None if not found

        Raises:
            ValueError: If book with the same title already exists
        """
        # Get book by ID
        book = await self.get_book_by_id(book_id)
        if not book:
            return None

        # Check title uniqueness if it's provided
        if book_data.title is not None and book_data.title != book.title:
            existing_book = await self.get_book_by_title(book_data.title)
            if existing_book and existing_book.id != book_id:
                error_msg = f"Book with title '{book_data.title}' already exists"
                logger.warning(error_msg)
                raise ValueError(error_msg)

        # Update basic fields
        update_data = book_data.model_dump(exclude={"categories", "tags", "authors"}, exclude_unset=True)
        for key, value in update_data.items():
            setattr(book, key, value)

        # Update categories if provided
        if book_data.categories is not None:
            stmt = books_categories.delete().where(books_categories.c.book_id == book_id)
            await self.session.execute(stmt)

            for category_id in book_data.categories:
                stmt = books_categories.insert().values(book_id=book_id, category_id=category_id)
                await self.session.execute(stmt)

        # Update tags if provided
        if book_data.tags is not None:
            stmt = books_tags.delete().where(books_tags.c.book_id == book_id)
            await self.session.execute(stmt)

            for tag_id in book_data.tags:
                stmt = books_tags.insert().values(book_id=book_id, tag_id=tag_id)
                await self.session.execute(stmt)

        # Update authors if provided
        if book_data.authors is not None:
            stmt = book_authors.delete().where(book_authors.c.book_id == book_id)
            await self.session.execute(stmt)

            for author_id in book_data.authors:
                stmt = book_authors.insert().values(book_id=book_id, author_id=author_id)
                await self.session.execute(stmt)

        await self.session.commit()

        # Reload the book with all relationships
        updated_book = await self.get_book_by_id(book_id)

        logger.info(f"Book partially updated: '{updated_book.title}' (ID: {updated_book.id})")
        return updated_book

    async def delete_book(self, book_id: int) -> bool:
        """
        Delete a book by ID.

        Args:
            book_id: Book identifier

        Returns:
            True if book was deleted, False if not found
        """
        book = await self.get_book_by_id(book_id)
        if not book:
            return False

        await self.session.delete(book)
        await self.session.commit()

        logger.info(f"Book deleted: ID {book_id}, title '{book.title}'")
        return True

    async def search_books(self, query: str, limit: int = 10, field: str = None) -> List[Book]:
        """
        Search for books by title and description using full-text search.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            field: Optional field to search in ('title', 'description', None for all fields)

        Returns:
            List of matching books with loaded relationships
        """
        try:
            # Проверяем входные параметры
            if not query or len(query.strip()) < 3:
                logger.warning("Поисковый запрос слишком короткий (минимум 3 символа)")
                return []

            logger.info(f"Выполняется полнотекстовый поиск: '{query}'{f' в поле {field}' if field else ''}")

            # Проверяем наличие фразовых запросов (в кавычках)
            has_phrase = '"' in query

            # Проверяем наличие операторов логики
            has_operators = any(op in query for op in ["&", "|", "!"])

            # Если нет операторов и фраз, подготавливаем запрос с учетом морфологии
            if not has_operators and not has_phrase:
                # Используем функцию преобразования для учета морфологии
                words = [word.strip() for word in query.strip().split() if len(word.strip()) > 2]
                cleaned_query = " & ".join([f"{word}:*" for word in words])
            else:
                # Если есть операторы или фразы, оставляем запрос как есть
                cleaned_query = query.strip()

            if not cleaned_query:
                logger.warning(f"После очистки поисковый запрос пустой: исходный запрос '{query}'")
                return []

            logger.debug(f"Поисковый запрос после преобразования: '{cleaned_query}'")

            try:
                # Сначала проверяем, что ts_query не вызывает ошибок синтаксиса
                check_syntax_sql = "SELECT to_tsquery('russian', :query)"
                await self.session.execute(text(check_syntax_sql), {"query": cleaned_query})

                # Выбираем поле для поиска в зависимости от параметра field
                if field == "title":
                    # Поиск только по названию
                    search_stmt = text(
                        """
                        SELECT b.id, ts_rank(
                            setweight(to_tsvector('russian', coalesce(b.title, '')), 'A'),
                            to_tsquery('russian', :query)
                        ) as rank
                        FROM books b
                        WHERE setweight(to_tsvector('russian', coalesce(b.title, '')), 'A') @@ to_tsquery('russian', :query)
                        ORDER BY rank DESC
                        LIMIT :limit
                    """
                    )
                elif field == "description":
                    # Поиск только по описанию
                    search_stmt = text(
                        """
                        SELECT b.id, ts_rank(
                            setweight(to_tsvector('russian', coalesce(b.description, '')), 'B'),
                            to_tsquery('russian', :query)
                        ) as rank
                        FROM books b
                        WHERE setweight(to_tsvector('russian', coalesce(b.description, '')), 'B') @@ to_tsquery('russian', :query)
                        ORDER BY rank DESC
                        LIMIT :limit
                    """
                    )
                else:
                    # Поиск по всем полям с разными весами
                    search_stmt = text(
                        """
                        SELECT b.id, ts_rank_cd(
                            setweight(to_tsvector('russian', coalesce(b.title, '')), 'A') ||
                            setweight(to_tsvector('russian', coalesce(b.description, '')), 'B') ||
                            setweight(to_tsvector('russian', coalesce(b.isbn, '')), 'C') ||
                            setweight(to_tsvector('russian', coalesce(b.publisher, '')), 'D'),
                            to_tsquery('russian', :query),
                            32  -- Нормализация для более точного ранжирования
                        ) as rank
                        FROM books b
                        WHERE b.search_vector @@ to_tsquery('russian', :query)
                        ORDER BY rank DESC
                        LIMIT :limit
                    """
                    )

                result = await self.session.execute(search_stmt, {"query": cleaned_query, "limit": limit})
                rows = result.fetchall()
                book_ids = [row[0] for row in rows]

            except Exception as e:
                logger.error(f"Ошибка при выполнении SQL запроса поиска: {str(e)}", exc_info=True)
                # Пробуем более простой поиск по словам без операторов
                words = [word.strip() for word in query.strip().split() if len(word.strip()) > 2]
                fallback_query = " | ".join([f"{word}:*" for word in words])
                logger.info(f"Используем запасной поисковый запрос: '{fallback_query}'")

                # Используем более простой запрос для запасного варианта
                search_stmt = text(
                    """
                    SELECT b.id
                    FROM books b
                    WHERE b.search_vector @@ to_tsquery('russian', :query)
                    LIMIT :limit
                """
                )

                result = await self.session.execute(search_stmt, {"query": fallback_query, "limit": limit})
                book_ids = [row[0] for row in result.fetchall()]

            # Если книги найдены, загружаем их с отношениями
            if book_ids:
                logger.info(f"Найдено {len(book_ids)} книг по запросу '{query}'")
                books_query = (
                    select(Book)
                    .where(Book.id.in_(book_ids))
                    .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
                )

                result = await self.session.execute(books_query)
                books = list(result.scalars().all())

                # Сортируем книги в том же порядке, что и в результатах поиска
                if len(book_ids) > 0 and len(books) > 0:
                    books_dict = {book.id: book for book in books}
                    sorted_books = [books_dict[book_id] for book_id in book_ids if book_id in books_dict]
                    return sorted_books
                else:
                    return books
            else:
                logger.info(f"По запросу '{query}' книги не найдены")
                return []

        except Exception as e:
            logger.error(f"Ошибка при полнотекстовом поиске книг: {str(e)}", exc_info=True)
            return []

    async def search_books_by_author(self, author_name: str, limit: int = 10) -> List[Book]:
        """
        Search for books by author name.

        Args:
            author_name: Author name to search for
            limit: Maximum number of results to return

        Returns:
            List of books by the specified author
        """
        try:
            # Проверяем входные параметры
            if not author_name or len(author_name.strip()) < 3:
                logger.warning("Имя автора слишком короткое (минимум 3 символа)")
                return []

            logger.info(f"Поиск книг по автору: '{author_name}'")

            # Проверяем наличие фразовых запросов (в кавычках)
            has_phrase = '"' in author_name

            # Если нет фраз, подготавливаем запрос с учетом морфологии
            if not has_phrase:
                # Используем функцию преобразования для учета морфологии
                words = [word.strip() for word in author_name.strip().split() if len(word.strip()) > 2]
                query_with_morphology = " | ".join([f"{w}:*" for w in words])
            else:
                # Если есть фразы, оставляем запрос как есть
                query_with_morphology = author_name.strip()

            # Ищем автора по имени, используя полнотекстовый поиск если есть вектор поиска
            try:
                author_query_ts = text(
                    """
                    SELECT a.id, ts_rank_cd(a.search_vector, to_tsquery('russian', :query)) as rank
                    FROM authors a
                    WHERE a.search_vector @@ to_tsquery('russian', :query)
                    ORDER BY rank DESC
                    LIMIT 10
                """
                )

                result = await self.session.execute(author_query_ts, {"query": query_with_morphology})

                author_ids_ts = [row[0] for row in result.fetchall()]

                if author_ids_ts:
                    logger.info(f"Найдено {len(author_ids_ts)} авторов по полнотекстовому поиску '{author_name}'")
                    author_ids = author_ids_ts
                else:
                    # Используем обычный поиск по частичному совпадению
                    author_query = select(Author.id).where(func.lower(Author.name).contains(author_name.lower()))

                    result = await self.session.execute(author_query)
                    author_ids = [row[0] for row in result.fetchall()]
                    logger.info(f"Найдено {len(author_ids)} авторов по частичному совпадению '{author_name}'")
            except Exception as e:
                logger.warning(f"Ошибка при поиске по вектору автора, используем обычный поиск: {str(e)}")
                # Используем обычный поиск как запасной вариант
                author_query = select(Author.id).where(func.lower(Author.name).contains(author_name.lower()))

                result = await self.session.execute(author_query)
                author_ids = [row[0] for row in result.fetchall()]
                logger.info(f"Найдено {len(author_ids)} авторов по частичному совпадению '{author_name}'")

            if not author_ids:
                logger.info(f"Авторы с именем '{author_name}' не найдены")
                return []

            # Получаем книги для всех найденных авторов
            books_query = (
                select(Book)
                .join(book_authors, Book.id == book_authors.c.book_id)
                .where(book_authors.c.author_id.in_(author_ids))
                .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
                .limit(limit)
            )

            result = await self.session.execute(books_query)
            books = list(result.scalars().all())

            logger.info(f"Найдено {len(books)} книг для авторов по запросу '{author_name}'")
            return books

        except Exception as e:
            logger.error(f"Ошибка при поиске книг по автору: {str(e)}", exc_info=True)
            return []

    async def update_search_vectors(self) -> int:
        """
        Update search vectors for all books.
        Creates/updates tsvector column with weighted title and description for full-text search.

        Returns:
            Number of books updated
        """
        try:
            logger.info("Обновление поисковых векторов для всех книг")

            # SQL запрос для обновления search_vector с улучшенными весовыми коэффициентами
            # A - наибольший вес (title), B - средний вес (description), C - низкий вес (isbn), D - самый низкий вес (publisher)
            sql = text(
                """
                UPDATE books
                SET search_vector =
                    setweight(to_tsvector('russian', coalesce(title, '')), 'A') ||
                    setweight(to_tsvector('russian', coalesce(description, '')), 'B') ||
                    setweight(to_tsvector('russian', coalesce(isbn, '')), 'C') ||
                    setweight(to_tsvector('russian', coalesce(publisher, '')), 'D')
            """
            )

            await self.session.execute(sql)

            # Также обновляем поисковые векторы для авторов
            author_sql = text(
                """
                UPDATE authors
                SET search_vector = to_tsvector('russian', coalesce(name, ''))
            """
            )

            await self.session.execute(author_sql)

            # Обновляем поисковые векторы для категорий
            category_sql = text(
                """
                UPDATE categories
                SET search_vector = to_tsvector('russian', coalesce(name_categories, ''))
            """
            )

            await self.session.execute(category_sql)

            # Обновляем поисковые векторы для тегов
            tag_sql = text(
                """
                UPDATE tags
                SET search_vector = to_tsvector('russian', coalesce(name_tag, ''))
            """
            )

            await self.session.execute(tag_sql)

            await self.session.commit()

            # Получаем количество обновленных книг
            count_query = select(func.count()).select_from(Book)
            count_result = await self.session.execute(count_query)
            count = count_result.scalar()

            logger.info(f"Поисковые векторы обновлены для {count} книг и связанных сущностей")
            return count

        except Exception as e:
            logger.error(f"Ошибка при обновлении поисковых векторов: {str(e)}", exc_info=True)
            await self.session.rollback()
            raise

    async def search_by_field(self, field: str, query: str, limit: int = 10) -> List[Book]:
        """
        Поиск книг по конкретному полю.

        Args:
            field: Поле для поиска ('title', 'description', 'publisher', 'isbn')
            query: Поисковый запрос
            limit: Максимальное количество результатов

        Returns:
            Список найденных книг
        """
        valid_fields = ["title", "description", "publisher", "isbn"]
        if field not in valid_fields:
            logger.error(f"Неверное поле для поиска: {field}")
            return []

        try:
            logger.info(f"Поиск по полю {field}: '{query}'")

            # Используем функцию преобразования для учета морфологии
            words = [word.strip() for word in query.strip().split() if len(word.strip()) > 2]

            if not words:
                logger.warning(f"Поисковый запрос слишком короткий: '{query}'")
                return []

            query_with_morphology = " | ".join([f"{w}:*" for w in words])

            search_stmt = text(
                f"""
                SELECT b.id, ts_rank_cd(
                    to_tsvector('russian', coalesce(b.{field}, '')),
                    to_tsquery('russian', :query)
                ) as rank
                FROM books b
                WHERE to_tsvector('russian', coalesce(b.{field}, '')) @@ to_tsquery('russian', :query)
                ORDER BY rank DESC
                LIMIT :limit
            """
            )

            result = await self.session.execute(search_stmt, {"query": query_with_morphology, "limit": limit})
            book_ids = [row[0] for row in result.fetchall()]

            if not book_ids:
                logger.info(f"По запросу '{query}' в поле '{field}' книги не найдены")
                return []

            books_query = (
                select(Book)
                .where(Book.id.in_(book_ids))
                .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            )

            result = await self.session.execute(books_query)
            books = list(result.scalars().all())

            # Сортируем книги в том же порядке, что и в результатах поиска
            if len(book_ids) > 0 and len(books) > 0:
                books_dict = {book.id: book for book in books}
                sorted_books = [books_dict[book_id] for book_id in book_ids if book_id in books_dict]
                logger.info(f"Найдено {len(sorted_books)} книг по запросу '{query}' в поле '{field}'")
                return sorted_books
            else:
                logger.info(f"Найдено {len(books)} книг по запросу '{query}' в поле '{field}'")
                return books

        except Exception as e:
            logger.error(f"Ошибка при поиске по полю {field}: {str(e)}", exc_info=True)
            return []
