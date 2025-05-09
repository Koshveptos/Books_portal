from datetime import UTC, datetime

from auth import current_active_user
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from models.book import Author, Book, Category, Tag
from models.user import User
from schemas.book import (
    BookCreate,
    BookPartial,
    BookResponse,
    BookUpdate,
    CategoryCreate,
    TagCreate,
)
from sqlalchemy import select, text
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.post("/update-search-vectors")
async def update_search_vectors(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        update_stmt = text(
            """
            UPDATE books
            SET search_vector =
                to_tsvector('russian', coalesce(title, '')) || ' ' ||
                to_tsvector('russian', coalesce(description, ''))
        """
        )
        await db.execute(update_stmt)
        await db.commit()
        return {"message": "Search vectors updated successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating search vectors: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/search", response_model=list[BookResponse])
async def search_books(
    query: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    if not query or len(query.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters long")

    sql = """
        SELECT b.id, b.title, b.year, b.publisher, b.isbn,
               b.description, b.cover, b.language, b.file_url,
               b.created_at, b.updated_at,
               array_agg(DISTINCT a.id) as author_ids,
               array_agg(DISTINCT c.name_categories) as category_names,
               array_agg(DISTINCT t.name_tag) as tag_names,
               ts_rank(b.search_vector, plainto_tsquery('russian', :query)) as rank
        FROM books b
        LEFT JOIN book_authors ba ON b.id = ba.book_id
        LEFT JOIN authors a ON ba.author_id = a.id
        LEFT JOIN book_categories bc ON b.id = bc.book_id
        LEFT JOIN categories c ON bc.category_id = c.id
        LEFT JOIN book_tags bt ON b.id = bt.book_id
        LEFT JOIN tags t ON bt.tag_id = t.id
        WHERE b.search_vector @@ plainto_tsquery('russian', :query)
        GROUP BY b.id
        ORDER BY rank DESC
        LIMIT 10
    """

    result = await db.execute(text(sql), {"query": query})
    rows = result.fetchall()

    books = []
    for row in rows:
        # Получаем полные объекты авторов
        authors_result = await db.execute(select(Author).where(Author.id.in_(row.author_ids)))
        authors = authors_result.scalars().all()

        # Получаем полные объекты категорий
        categories_result = await db.execute(select(Category).where(Category.name_categories.in_(row.category_names)))
        categories = categories_result.scalars().all()

        # Получаем полные объекты тегов
        tags_result = await db.execute(select(Tag).where(Tag.name_tag.in_(row.tag_names)))
        tags = tags_result.scalars().all()

        book = BookResponse(
            id=row.id,
            title=row.title,
            year=row.year,
            publisher=row.publisher,
            isbn=row.isbn,
            description=row.description,
            cover=row.cover,
            language=row.language,
            file_url=row.file_url,
            created_at=row.created_at,
            updated_at=row.updated_at,
            authors=authors,
            categories=categories,
            tags=tags,
        )
        books.append(book)
    return books


@router.get("/suggest", response_model=list[str])
async def suggest_corrections(
    query: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    if not query or len(query.strip()) < 3:
        return []

    sql = """
        SELECT word, similarity
        FROM (
            SELECT title as word, similarity(title, :query) as similarity
            FROM books
            WHERE title % :query
            UNION
            SELECT name as word, similarity(name, :query) as similarity
            FROM authors
            WHERE name % :query
            UNION
            SELECT name_categories as word, similarity(name_categories, :query) as similarity
            FROM categories
            WHERE name_categories % :query
            UNION
            SELECT name_tag as word, similarity(name_tag, :query) as similarity
            FROM tags
            WHERE name_tag % :query
        ) as words
        WHERE similarity > 0.3
        ORDER BY similarity DESC
        LIMIT 5
    """
    result = await db.execute(text(sql), {"query": query.strip()})
    return [row.word for row in result.fetchall()]


@router.get("/", response_model=list[BookResponse])
async def get_books(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Получить список всех книг.
    """
    try:
        logger.info("Get all books")
        query = (
            select(Book)
            .order_by(Book.id)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
        )
        result: Result = await db.execute(query)
        books = result.scalars().all()
        logger.debug("All books got successfully")
        return list(books)
    except Exception as e:
        logger.error(f"Internal server error {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Получить книгу по её ID.
    """
    try:
        logger.info("Get book by id")
        query = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == book_id)
        )
        result = await db.execute(query)
        book = result.scalars().first()
        if book:
            return book
        else:
            logger.error(f"Book with id {book_id} not found")
            raise HTTPException(status_code=404, detail="Book not found")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while getting book: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/", response_model=BookResponse)
async def create_book(
    book: BookCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Создать новую книгу.
    """
    if not user.is_superuser and not user.is_moderator:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        logger.debug(f"Start to create Book: {book.model_dump()}")
        logger.debug("Get Authors, Tags and Categories from db")

        # проверка существования авторов
        authors_id = book.authors
        authors_result = await db.execute(select(Author).where(Author.id.in_(authors_id)))
        authors = authors_result.scalars().all()
        if len(authors) != len(authors_id):
            missing_authors = set(authors_id) - {a.id for a in authors}
            logger.error(f"Missing some authors: {missing_authors}")
            raise HTTPException(status_code=400, detail=f"Authors with IDs {missing_authors} do not exist")

        # проверка существования тегов
        tags_id = book.tags
        tags_result = await db.execute(select(Tag).where(Tag.id.in_(tags_id)))
        tags = tags_result.scalars().all()
        if len(tags) != len(tags_id):
            missing_tags = set(tags_id) - {t.id for t in tags}
            logger.error(f"Missing some tags: {missing_tags}")
            raise HTTPException(status_code=400, detail=f"Tags with IDs {missing_tags} do not exist")

        # проверка существования категорий
        categories_id = book.categories
        categories_result = await db.execute(select(Category).where(Category.id.in_(categories_id)))
        categories = categories_result.scalars().all()
        if len(categories) != len(categories_id):
            missing_categories = set(categories_id) - {c.id for c in categories}
            logger.error(f"Missing some categories: {missing_categories}")
            raise HTTPException(status_code=400, detail=f"Categories with IDs {missing_categories} do not exist")

        # Создание книги
        db_book = Book(**book.model_dump(exclude={"authors", "categories", "tags"}))
        db_book.authors = authors
        db_book.tags = tags
        db_book.categories = categories
        db_book.created_at = datetime.now(UTC)
        db_book.updated_at = datetime.now(UTC)

        db.add(db_book)
        await db.commit()
        await db.refresh(db_book)

        # Явная загрузка связанных объектов
        db_book = await db.get(Book, db_book.id)
        db_book.authors = await db.run_sync(lambda _: db_book.authors)
        db_book.categories = await db.run_sync(lambda _: db_book.categories)
        db_book.tags = await db.run_sync(lambda _: db_book.tags)
        logger.info(f"Book created successfully with ID {db_book.id}")
        return db_book
    except HTTPException:
        raise
    except IntegrityError:
        await db.rollback()
        logger.error("IntegrityError while creating book")
        raise HTTPException(status_code=400, detail="Book already exists")
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while creating book: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_update: BookUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Полностью обновить книгу по её ID.
    """
    if not user.is_superuser and not user.is_moderator:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        logger.info(f"Update informations about book{book_id}")
        query = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == book_id)
        )

        result = await db.execute(query)
        book = result.scalars().first()
        if not book:
            logger.error(f"Book with ID {book_id} does not exist")
            raise HTTPException(status_code=404, detail="Book not found")

        for name, value in book_update.model_dump(exclude={"authors", "tags", "categories"}).items():
            setattr(book, name, value)

        # обновление авторов
        if book_update.authors:
            authors_result = await db.execute(select(Author).where(Author.id.in_(book_update.authors)))
            authors = authors_result.scalars().all()
            if len(authors) != len(book_update.authors):
                missing_authors = set(book_update.authors) - set(a.id for a in authors)
                logger.error(f"Missing authors{missing_authors}")
                raise HTTPException(status_code=400, detail=f"Authors {missing_authors} not found")
            book.authors = authors

        # обновление категорий
        if book_update.categories:
            categories_result = await db.execute(select(Category).where(Category.id.in_(book_update.categories)))
            categories = categories_result.scalars().all()
            if len(categories) != len(book_update.categories):
                missing_categories = set(book_update.categories) - set(c.id for c in categories)
                logger.error(f"Missing categories{missing_categories}")
                raise HTTPException(status_code=400, detail=f"Categories {missing_categories} not found")
            book.categories = categories

        # обновление тегов
        if book_update.tags:
            tags_result = await db.execute(select(Tag).where(Tag.id.in_(book_update.tags)))
            tags = tags_result.scalars().all()
            if len(tags) != len(book_update.tags):
                missing_tags = set(book_update.tags) - set(t.id for t in tags)
                logger.error(f"Missing tags{missing_tags}")
                raise HTTPException(status_code=400, detail=f"Tags {missing_tags} not found")
            book.tags = tags

        await db.commit()
        await db.refresh(book)
        logger.debug(f"Book with ID {book.id} successfully upgraded")
        return book
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError while updating book: {str(e)}")
        raise HTTPException(status_code=400, detail="Book data is invalid or already exists")
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while updating books{e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.patch("/{book_id}", response_model=BookResponse)
async def partial_update_book(
    book_id: int,
    book_update: BookPartial,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Частично обновить книгу по её ID.
    """
    if not user.is_superuser and not user.is_moderator:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        logger.info(f"Partial update book with ID {book_id}")
        query = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == book_id)
        )
        result = await db.execute(query)
        book = result.scalars().first()
        if not book:
            logger.error(f"Book with ID {book_id} does not exist")
            raise HTTPException(status_code=404, detail="Book not found")

        update_data = book_update.model_dump(exclude={"authors", "tags", "categories"}, exclude_unset=True)
        for name, value in update_data.items():
            setattr(book, name, value)

        # Обновляем авторов, если они указаны в запросе
        if book_update.authors is not None:
            authors_result = await db.execute(select(Author).where(Author.id.in_(book_update.authors)))
            authors = authors_result.scalars().all()
            if len(authors) != len(book_update.authors):
                missing_authors = set(book_update.authors) - set(a.id for a in authors)
                logger.error(f"Missing authors: {missing_authors}")
                raise HTTPException(status_code=400, detail=f"Authors {missing_authors} not found")
            book.authors = authors

        # Обновляем категории, если они указаны в запросе
        if book_update.categories is not None:
            categories_result = await db.execute(select(Category).where(Category.id.in_(book_update.categories)))
            categories = categories_result.scalars().all()
            if len(categories) != len(book_update.categories):
                missing_categories = set(book_update.categories) - set(c.id for c in categories)
                logger.error(f"Missing categories: {missing_categories}")
                raise HTTPException(status_code=400, detail=f"Categories {missing_categories} not found")
            book.categories = categories

        # Обновляем теги, если они указаны в запросе
        if book_update.tags is not None:
            tags_result = await db.execute(select(Tag).where(Tag.id.in_(book_update.tags)))
            tags = tags_result.scalars().all()
            if len(tags) != len(book_update.tags):
                missing_tags = set(book_update.tags) - set(t.id for t in tags)
                logger.error(f"Missing tags: {missing_tags}")
                raise HTTPException(status_code=400, detail=f"Tags {missing_tags} not found")
            book.tags = tags

        await db.commit()
        await db.refresh(book)
        logger.debug(f"Book with ID {book.id} successfully upgraded")
        return book
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError while updating book: {str(e)}")
        raise HTTPException(status_code=400, detail="Book data is invalid or already exists")
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while updating books{e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/{book_id}", response_model=dict)
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Удалить книгу по её ID.
    """
    if not user.is_superuser and not user.is_moderator:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        book = await db.get(Book, book_id)
        if not book:
            logger.error(f"Book with ID {book_id} not found")
            raise HTTPException(status_code=404, detail="Book not found")
        await db.delete(book)
        await db.commit()
        logger.debug(f"Book with ID {book_id} successfully deleted")
        return {"message": "Book deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting Book with ID {book_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/category", response_model=CategoryCreate)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Создать категорию.
    """
    if not user.is_superuser and not user.is_moderator:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    category_db = Category(**category.model_dump())
    db.add(category_db)
    await db.commit()
    await db.refresh(category_db)
    return category_db


@router.post("/tag", response_model=TagCreate)
async def create_tag(
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Создать тег.
    """
    if not user.is_superuser and not user.is_moderator:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    tag_db = Tag(**tag.model_dump())
    db.add(tag_db)
    await db.commit()
    await db.refresh(tag_db)
    return tag_db
