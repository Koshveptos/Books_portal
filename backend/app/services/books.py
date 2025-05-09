from typing import List, Optional

from core.logger_config import logger
from models.book import Book, book_authors, books_categories, books_tags
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

    async def search_books(self, query: str, limit: int = 10) -> List[Book]:
        """
        Search for books using full-text search.

        Args:
            query: Search query
            limit: Maximum number of results to return

        Returns:
            List of matching books
        """
        # Use the search_vector column for full-text search
        search_stmt = (
            select(Book)
            .options(selectinload(Book.categories), selectinload(Book.tags), selectinload(Book.authors))
            .where(Book.search_vector.op("@@")(func.to_tsquery("russian", query.replace(" ", " & "))))
            .limit(limit)
        )

        result = await self.session.execute(search_stmt)
        books = list(result.scalars().all())

        logger.info(f"Search for '{query}' returned {len(books)} results")
        return books

    async def update_search_vectors(self) -> int:
        """
        Update search vectors for all books.

        Returns:
            Number of books updated
        """
        # SQL to update the search_vector column with concatenated text from relevant columns
        sql = text(
            """
            UPDATE books SET search_vector =
            setweight(to_tsvector('russian', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('russian', coalesce(description, '')), 'B') ||
            setweight(to_tsvector('russian', coalesce(publisher, '')), 'C')
        """
        )

        await self.session.execute(sql)
        await self.session.commit()

        # Get the count of books
        count_query = select(func.count()).select_from(Book)
        count_result = await self.session.execute(count_query)
        count = count_result.scalar()

        logger.info(f"Updated search vectors for {count} books")
        return count
