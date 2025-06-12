"""
Маршруты для работы с книгами.
"""

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import current_active_user
from app.core.dependencies import get_db, get_redis_client
from app.core.exceptions import (
    BookNotFoundException,
    CategoryNotFoundException,
    DatabaseException,
    InvalidBookDataException,
    InvalidCategoryDataException,
    InvalidTagDataException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.core.logger_config import (
    log_cache_error,
    log_db_error,
    log_info,
    log_validation_error,
    log_warning,
)
from app.models.book import Author, Book, Category, Tag
from app.models.user import User
from app.schemas.book import (
    AuthorResponse,
    BookCreate,
    BookPartial,
    BookResponse,
    BookUpdate,
    CategoryCreate,
    CategoryResponse,
    TagCreate,
    TagResponse,
    UserRatingResponse,
)
from app.services.book import BookService
from app.utils.json_serializer import deserialize_from_json, serialize_to_json

router = APIRouter(tags=["books"])
books_router = APIRouter(tags=["books"])

# Маршруты поиска и обновления векторов перенесены в routers/search.py


@router.get("/", response_model=List[BookResponse])
async def get_books(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    use_cache: bool = True,
):
    """
    Получить список всех книг. Публичный эндпоинт.
    """
    try:
        log_info("Getting all books")

        # Пытаемся получить книги из кэша
        if use_cache and redis_client is not None:
            try:
                cached_books = await redis_client.get(f"books:all:{skip}:{limit}")
                if cached_books:
                    try:
                        books_data = deserialize_from_json(cached_books)
                        log_info(f"Successfully retrieved {len(books_data)} books from cache")
                        return [BookResponse(**book) for book in books_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_books",
                                "key": f"books:all:{skip}:{limit}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_books",
                        "key": f"books:all:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Если кэш недоступен или пуст, получаем из БД
        query = (
            select(Book)
            .order_by(Book.id)
            .offset(skip)
            .limit(limit)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
        )
        result: Result = await db.execute(query)
        books = result.scalars().all()

        # Преобразуем книги в модели Pydantic, проверяя, что все связи загружены
        book_responses = []
        for book in books:
            try:
                if not (hasattr(book, "authors") and hasattr(book, "categories") and hasattr(book, "tags")):
                    book_id = book.id
                    query = (
                        select(Book)
                        .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
                        .where(Book.id == book_id)
                    )
                    result = await db.execute(query)
                    book = result.scalar_one()

                book_responses.append(BookResponse.model_validate(book))
            except Exception as e:
                log_db_error(
                    e,
                    {
                        "operation": "get_books_validation",
                        "table": "books",
                        "book_id": str(book.id),
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )
                continue  # Пропускаем книгу с ошибкой валидации

        if not book_responses:
            log_info("No books found")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"message": "Книги не найдены"},
            )

        log_info(f"Successfully retrieved {len(book_responses)} books")

        # Сохраняем в кэш
        if use_cache and redis_client is not None:
            try:
                await redis_client.set(
                    f"books:all:{skip}:{limit}",
                    serialize_to_json(book_responses),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached {len(book_responses)} books")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_books",
                        "key": f"books:all:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return book_responses
    except SQLAlchemyError as e:
        log_db_error(
            e,
            {
                "operation": "get_all_books",
                "table": "books",
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Ошибка при получении списка книг из базы данных")
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_all_books",
                "table": "books",
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Непредвиденная ошибка при получении списка книг")


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> BookResponse:
    """
    Получение книги по ID.

    Args:
        book_id: ID книги
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        BookResponse: Информация о книге

    Raises:
        HTTPException: Если книга не найдена или произошла ошибка
    """
    try:
        log_info(f"Getting book with ID: {book_id}")

        # Пытаемся получить книгу из кэша
        if redis_client is not None:
            try:
                cache_key = f"book:{book_id}"
                cached_book = await redis_client.get(cache_key)
                if cached_book:
                    try:
                        book_data = deserialize_from_json(cached_book)
                        log_info(f"Successfully retrieved book {book_id} from cache")
                        return BookResponse(**book_data)
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_book",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_book",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Если кэш недоступен или пуст, получаем из БД
        query = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == book_id)
        )
        result = await db.execute(query)
        book = result.scalars().first()

        if not book:
            log_warning(f"Book with ID {book_id} not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Книга с ID {book_id} не найдена")

        book_response = BookResponse.model_validate(book)
        log_info(f"Successfully retrieved book with ID: {book_id}")

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(book_response),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached book {book_id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_book",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return book_response
    except HTTPException:
        raise
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_book",
                "book_id": book_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении книги")


# Добавляем те же роуты к books_router для доступа через прямой URL
@books_router.get("/", response_model=list[BookResponse])
async def get_books_flat(db: AsyncSession = Depends(get_db)):
    """
    Получить список всех книг через прямой URL /books. Публичный эндпоинт.
    """
    return await get_books(db)


@books_router.get("/{book_id}", response_model=BookResponse)
async def get_book_flat(book_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получить книгу по её ID через прямой URL /books/{book_id}. Публичный эндпоинт.
    """
    return await get_book(book_id, db)


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book: BookCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Создать новую книгу.
    """
    try:
        if not user.is_superuser and not user.is_moderator:
            log_warning(f"User {user.id} attempted to create book without sufficient permissions")
            raise PermissionDeniedException("Недостаточно прав для создания книги")

        log_info(f"Creating new book: {book.title}")

        # Проверка существования авторов
        authors_result = await db.execute(select(Author).where(Author.id.in_(book.authors)))
        authors = authors_result.scalars().all()
        if len(authors) != len(book.authors):
            missing_authors = set(book.authors) - set(a.id for a in authors)
            log_validation_error(ValueError(f"Missing authors: {missing_authors}"), model_name="Book", field="authors")
            raise ResourceNotFoundException(f"Авторы {missing_authors} не найдены")

        # Проверка существования категорий
        categories_result = await db.execute(select(Category).where(Category.id.in_(book.categories)))
        categories = categories_result.scalars().all()
        if len(categories) != len(book.categories):
            missing_categories = set(book.categories) - set(c.id for c in categories)
            log_validation_error(
                ValueError(f"Missing categories: {missing_categories}"), model_name="Book", field="categories"
            )
            raise ResourceNotFoundException(f"Категории {missing_categories} не найдены")

        # Проверка существования тегов
        tags_result = await db.execute(select(Tag).where(Tag.id.in_(book.tags)))
        tags = tags_result.scalars().all()
        if len(tags) != len(book.tags):
            missing_tags = set(book.tags) - set(t.id for t in tags)
            log_validation_error(ValueError(f"Missing tags: {missing_tags}"), model_name="Book", field="tags")
            raise ResourceNotFoundException(f"Теги {missing_tags} не найдены")

        # Создание объекта книги
        book_dict = book.model_dump(exclude={"authors", "categories", "tags"})
        log_info(f"Creating book with data: {book_dict}")

        db_book = Book(**book_dict)
        db_book.authors = authors
        db_book.categories = categories
        db_book.tags = tags

        try:
            db.add(db_book)
            await db.commit()
            await db.refresh(db_book)
        except IntegrityError as e:
            await db.rollback()
            log_db_error(e, operation="create_book", table="books", details=str(e))
            if "unique constraint" in str(e).lower():
                raise InvalidBookDataException("Книга с такими данными уже существует")
            raise InvalidBookDataException(f"Ошибка целостности данных при создании книги: {str(e)}")
        except SQLAlchemyError as e:
            await db.rollback()
            log_db_error(e, operation="create_book", table="books", details=str(e))
            raise DatabaseException(f"Ошибка при создании книги в базе данных: {str(e)}")

        log_info(f"Book created successfully with ID: {db_book.id}")

        # Загружаем объект со всеми связями
        try:
            result = await db.execute(
                select(Book)
                .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
                .where(Book.id == db_book.id)
            )
            book_with_relations = result.scalar_one()
            return BookResponse.model_validate(book_with_relations)
        except Exception as e:
            log_db_error(e, operation="create_book_load_relations", table="books", book_id=str(db_book.id))
            raise DatabaseException("Ошибка при загрузке связей созданной книги")
    except (PermissionDeniedException, ResourceNotFoundException):
        raise
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="create_book", table="books", details=str(e))
        raise DatabaseException(f"Непредвиденная ошибка при создании книги: {str(e)}")


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
    try:
        if not user.is_superuser and not user.is_moderator:
            log_warning(f"User {user.id} attempted to update book {book_id} without sufficient permissions")
            raise PermissionDeniedException("Недостаточно прав для обновления книги")

        log_info(f"Updating book with ID: {book_id}")

        query = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == book_id)
        )

        result = await db.execute(query)
        book = result.scalars().first()

        if not book:
            log_warning(f"Book with ID {book_id} not found")
            raise BookNotFoundException(f"Книга с ID {book_id} не найдена")

        # Обновление основных полей
        for name, value in book_update.model_dump(exclude={"authors", "tags", "categories"}).items():
            setattr(book, name, value)

        # Обновление авторов
        if book_update.authors:
            authors_result = await db.execute(select(Author).where(Author.id.in_(book_update.authors)))
            authors = authors_result.scalars().all()
            if len(authors) != len(book_update.authors):
                missing_authors = set(book_update.authors) - set(a.id for a in authors)
                log_validation_error(
                    ValueError(f"Missing authors: {missing_authors}"), model_name="Book", field="authors"
                )
                raise ResourceNotFoundException(f"Авторы {missing_authors} не найдены")
            book.authors = authors

        # Обновление категорий
        if book_update.categories:
            categories_result = await db.execute(select(Category).where(Category.id.in_(book_update.categories)))
            categories = categories_result.scalars().all()
            if len(categories) != len(book_update.categories):
                missing_categories = set(book_update.categories) - set(c.id for c in categories)
                log_validation_error(
                    ValueError(f"Missing categories: {missing_categories}"), model_name="Book", field="categories"
                )
                raise ResourceNotFoundException(f"Категории {missing_categories} не найдены")
            book.categories = categories

        # Обновление тегов
        if book_update.tags:
            tags_result = await db.execute(select(Tag).where(Tag.id.in_(book_update.tags)))
            tags = tags_result.scalars().all()
            if len(tags) != len(book_update.tags):
                missing_tags = set(book_update.tags) - set(t.id for t in tags)
                log_validation_error(ValueError(f"Missing tags: {missing_tags}"), model_name="Book", field="tags")
                raise ResourceNotFoundException(f"Теги {missing_tags} не найдены")
            book.tags = tags

        await db.commit()
        await db.refresh(book)

        log_info(f"Book {book_id} updated successfully")
        return BookResponse.model_validate(book)
    except (PermissionDeniedException, BookNotFoundException, ResourceNotFoundException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="update_book", table="books")
        if "unique constraint" in str(e).lower():
            raise InvalidBookDataException("Книга с такими данными уже существует")
        raise InvalidBookDataException("Некорректные данные для обновления книги")
    except SQLAlchemyError as e:
        await db.rollback()
        log_db_error(e, operation="update_book", table="books")
        raise DatabaseException("Ошибка при обновлении книги в базе данных")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="update_book", table="books")
        raise DatabaseException("Непредвиденная ошибка при обновлении книги")


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
    try:
        if not user.is_superuser and not user.is_moderator:
            log_warning(f"User {user.id} attempted to update book {book_id} without sufficient permissions")
            raise PermissionDeniedException("Недостаточно прав для обновления книги")

        log_info(f"Partially updating book with ID: {book_id}")

        query = (
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == book_id)
        )

        result = await db.execute(query)
        book = result.scalars().first()

        if not book:
            log_warning(f"Book with ID {book_id} not found")
            raise BookNotFoundException(f"Книга с ID {book_id} не найдена")

        # Обновление основных полей
        update_data = book_update.model_dump(exclude_unset=True, exclude={"authors", "tags", "categories"})
        for name, value in update_data.items():
            setattr(book, name, value)

        # Обновление авторов
        if book_update.authors is not None:
            authors_result = await db.execute(select(Author).where(Author.id.in_(book_update.authors)))
            authors = authors_result.scalars().all()
            if len(authors) != len(book_update.authors):
                missing_authors = set(book_update.authors) - set(a.id for a in authors)
                log_validation_error(
                    ValueError(f"Missing authors: {missing_authors}"), model_name="Book", field="authors"
                )
                raise InvalidBookDataException(f"Авторы {missing_authors} не найдены")
            book.authors = authors

        # Обновление категорий
        if book_update.categories is not None:
            categories_result = await db.execute(select(Category).where(Category.id.in_(book_update.categories)))
            categories = categories_result.scalars().all()
            if len(categories) != len(book_update.categories):
                missing_categories = set(book_update.categories) - set(c.id for c in categories)
                log_validation_error(
                    ValueError(f"Missing categories: {missing_categories}"), model_name="Book", field="categories"
                )
                raise InvalidBookDataException(f"Категории {missing_categories} не найдены")
            book.categories = categories

        # Обновление тегов
        if book_update.tags is not None:
            tags_result = await db.execute(select(Tag).where(Tag.id.in_(book_update.tags)))
            tags = tags_result.scalars().all()
            if len(tags) != len(book_update.tags):
                missing_tags = set(book_update.tags) - set(t.id for t in tags)
                log_validation_error(ValueError(f"Missing tags: {missing_tags}"), model_name="Book", field="tags")
                raise InvalidBookDataException(f"Теги {missing_tags} не найдены")
            book.tags = tags

        await db.commit()
        await db.refresh(book)

        log_info(f"Book {book_id} updated successfully")
        return BookResponse.model_validate(book)
    except (PermissionDeniedException, BookNotFoundException, InvalidBookDataException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="partial_update_book", table="books", book_id=str(book_id))
        raise InvalidBookDataException("Ошибка целостности данных при обновлении книги")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="partial_update_book", table="books", book_id=str(book_id))
        raise DatabaseException("Ошибка при обновлении книги")


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Удалить книгу по её ID.
    """
    try:
        if not user.is_superuser and not user.is_moderator:
            log_warning(f"User {user.id} attempted to delete book {book_id} without sufficient permissions")
            raise PermissionDeniedException("Недостаточно прав для удаления книги")

        log_info(f"Deleting book with ID: {book_id}")

        query = select(Book).where(Book.id == book_id)
        result = await db.execute(query)
        book = result.scalars().first()

        if not book:
            log_warning(f"Book with ID {book_id} not found")
            raise BookNotFoundException(f"Книга с ID {book_id} не найдена")

        await db.delete(book)
        await db.commit()

        log_info(f"Book {book_id} deleted successfully")
    except (PermissionDeniedException, BookNotFoundException):
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        log_db_error(e, operation="delete_book", table="books", book_id=str(book_id))
        raise DatabaseException("Ошибка при удалении книги из базы данных")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="delete_book", table="books", book_id=str(book_id))
        raise DatabaseException("Непредвиденная ошибка при удалении книги")


@router.post("/category", response_model=CategoryResponse)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Создать новую категорию.
    """
    try:
        if not user.is_superuser and not user.is_moderator:
            log_warning(f"User {user.id} attempted to create category without sufficient permissions")
            raise PermissionDeniedException("Недостаточно прав для создания категории")

        log_info(f"Creating new category: {category.name_categories}")

        # Проверка на существование категории с таким же названием
        existing_category = await db.execute(
            select(Category).where(Category.name_categories == category.name_categories)
        )
        if existing_category.scalar_one_or_none():
            log_warning(f"Category with name '{category.name_categories}' already exists")
            raise InvalidCategoryDataException("Категория с таким названием уже существует")

        db_category = Category(**category.model_dump())
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)

        log_info(f"Category created successfully with ID: {db_category.id}")
        return CategoryResponse.model_validate(db_category)
    except PermissionDeniedException:
        raise
    except InvalidCategoryDataException:
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="create_category", table="categories")
        raise InvalidCategoryDataException("Ошибка целостности данных при создании категории")
    except SQLAlchemyError as e:
        await db.rollback()
        log_db_error(e, operation="create_category", table="categories")
        raise DatabaseException("Ошибка при создании категории в базе данных")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="create_category", table="categories")
        raise DatabaseException("Непредвиденная ошибка при создании категории")


@router.post("/tag", response_model=TagResponse)
async def create_tag(
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Создать новый тег.
    """
    try:
        if not user.is_superuser and not user.is_moderator:
            log_warning(f"User {user.id} attempted to create tag without sufficient permissions")
            raise PermissionDeniedException("Недостаточно прав для создания тега")

        log_info(f"Creating new tag: {tag.name_tag}")

        # Проверка на существование тега с таким же названием
        existing_tag = await db.execute(select(Tag).where(Tag.name_tag == tag.name_tag))
        if existing_tag.scalar_one_or_none():
            log_warning(f"Tag with name '{tag.name_tag}' already exists")
            raise InvalidTagDataException("Тег с таким названием уже существует")

        db_tag = Tag(**tag.model_dump())
        db.add(db_tag)
        await db.commit()
        await db.refresh(db_tag)

        log_info(f"Tag created successfully with ID: {db_tag.id}")
        return TagResponse.model_validate(db_tag)
    except PermissionDeniedException:
        raise
    except InvalidTagDataException:
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="create_tag", table="tags")
        raise InvalidTagDataException("Ошибка целостности данных при создании тега")
    except SQLAlchemyError as e:
        await db.rollback()
        log_db_error(e, operation="create_tag", table="tags")
        raise DatabaseException("Ошибка при создании тега в базе данных")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="create_tag", table="tags")
        raise DatabaseException("Непредвиденная ошибка при создании тега")


# Для URL /books/ (без /books/books/)
@router.get("/books/", response_model=list[BookResponse])
async def get_all_books(
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список всех книг. Публичный эндпоинт с другим URL.
    """
    return await get_books(db)


# Для URL /books/books/
@router.get("/books/", response_model=list[BookResponse])
async def get_all_books_alt(
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список всех книг. Публичный эндпоинт с другим URL.
    """
    return await get_books(db)


@router.get("/by-category/{category_id}", response_model=list[BookResponse])
async def get_books_by_category(
    category_id: int,
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список книг по категории.

    Args:
        category_id: ID категории
        limit: Максимальное количество результатов
    """
    try:
        log_info(f"Getting books by category ID: {category_id}")

        # Проверяем существование категории
        category = await db.execute(select(Category).where(Category.id == category_id))
        if not category.scalar_one_or_none():
            log_warning(f"Category with ID {category_id} not found")
            raise CategoryNotFoundException(f"Категория с ID {category_id} не найдена")

        books_service = BookService(db)
        books = await books_service.get_books(category_id=category_id, limit=limit)

        if not books:
            log_info(f"No books found for category ID: {category_id}")
            return []

        log_info(f"Found {len(books)} books for category ID: {category_id}")
        return [BookResponse.model_validate(book) for book in books]

    except CategoryNotFoundException:
        raise
    except SQLAlchemyError as e:
        log_db_error(e, operation="get_books_by_category", table="books", category_id=str(category_id))
        raise DatabaseException("Ошибка при получении книг по категории")
    except Exception as e:
        log_db_error(e, operation="get_books_by_category", table="books", category_id=str(category_id))
        raise DatabaseException("Непредвиденная ошибка при получении книг по категории")


@router.get("/by-author/{author_id}", response_model=List[BookResponse])
async def get_books_by_author(
    author_id: int,
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
):
    """
    Получить список книг по автору.

    Args:
        author_id: ID автора
        limit: Максимальное количество результатов
        skip: Количество пропускаемых записей
    """
    try:
        log_info(f"Getting books by author ID: {author_id}")

        # Пытаемся получить книги из кэша
        if redis_client is not None:
            try:
                cached_books = await redis_client.get(f"books:author:{author_id}:{skip}:{limit}")
                if cached_books:
                    try:
                        books = deserialize_from_json(cached_books)
                        log_info(f"Successfully retrieved {len(books)} books from cache for author {author_id}")
                        return books
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_author_books",
                                "key": f"books:author:{author_id}:{skip}:{limit}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_books_by_author",
                        "key": f"books:author:{author_id}:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Проверяем существование автора
        author = await db.execute(select(Author).where(Author.id == author_id))
        if not author.scalar_one_or_none():
            log_warning(f"Author with ID {author_id} not found")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": f"Автор с ID {author_id} не найден"},
            )

        books_service = BookService(db)
        books = await books_service.get_books(author_id=author_id, limit=limit, skip=skip)

        if not books:
            log_info(f"No books found for author ID: {author_id}")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"message": f"Книги автора с ID {author_id} не найдены"},
            )

        book_responses = [BookResponse.model_validate(book) for book in books]
        log_info(f"Found {len(book_responses)} books for author ID: {author_id}")

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    f"books:author:{author_id}:{skip}:{limit}", serialize_to_json(book_responses), expire=3600  # 1 час
                )
                log_info(f"Successfully cached {len(book_responses)} books for author {author_id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_author_books",
                        "key": f"books:author:{author_id}:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return book_responses

    except SQLAlchemyError as e:
        log_db_error(
            e,
            {
                "operation": "get_books_by_author",
                "table": "books",
                "author_id": str(author_id),
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Ошибка при получении книг по автору")
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_books_by_author",
                "table": "books",
                "author_id": str(author_id),
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Непредвиденная ошибка при получении книг по автору")


@router.get("/authors", response_model=List[AuthorResponse])
async def get_authors(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
):
    """
    Получить список всех авторов.
    """
    try:
        log_info("Getting all authors")

        # Пытаемся получить авторов из кэша
        if redis_client is not None:
            try:
                cached_authors = await redis_client.get(f"authors:all:{skip}:{limit}")
                if cached_authors:
                    try:
                        authors = deserialize_from_json(cached_authors)
                        log_info(f"Successfully retrieved {len(authors)} authors from cache")
                        return authors
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_authors",
                                "key": f"authors:all:{skip}:{limit}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_authors",
                        "key": f"authors:all:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        query = select(Author).order_by(Author.name).offset(skip).limit(limit)
        result = await db.execute(query)
        authors = result.scalars().all()

        if not authors:
            log_info("No authors found")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"message": "Авторы не найдены"},
            )

        author_responses = [AuthorResponse.model_validate(author) for author in authors]
        log_info(f"Found {len(author_responses)} authors")

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    f"authors:all:{skip}:{limit}", serialize_to_json(author_responses), expire=3600  # 1 час
                )
                log_info(f"Successfully cached {len(author_responses)} authors")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_authors",
                        "key": f"authors:all:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return author_responses

    except SQLAlchemyError as e:
        log_db_error(
            e,
            {
                "operation": "get_authors",
                "table": "authors",
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Ошибка при получении списка авторов из базы данных")
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_authors",
                "table": "authors",
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Непредвиденная ошибка при получении списка авторов")


@router.get("/user/likes", response_model=List[BookResponse])
async def get_user_likes(
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Получить список книг, которые понравились пользователю.
    """
    try:
        log_info(f"User {user.email} getting liked books")

        books_service = BookService(db)
        books = await books_service.get_user_likes(user.id, limit=limit, skip=skip)

        if not books:
            log_info(f"No liked books found for user {user.email}")
            return []

        log_info(f"Found {len(books)} liked books for user {user.email}")
        return [BookResponse.model_validate(book) for book in books]

    except SQLAlchemyError as e:
        log_db_error(e, operation="get_user_likes", table="likes", user_id=str(user.id))
        raise DatabaseException("Ошибка при получении списка понравившихся книг из базы данных")
    except Exception as e:
        log_db_error(e, operation="get_user_likes", table="likes", user_id=str(user.id))
        raise DatabaseException("Непредвиденная ошибка при получении списка понравившихся книг")


@router.get("/user/favorites", response_model=List[BookResponse])
async def get_user_favorites(
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    user: User = Depends(current_active_user),
):
    """
    Получить список книг в избранном пользователя.
    """
    try:
        log_info(f"User {user.email} getting favorite books")

        # Пытаемся получить избранные книги из кэша
        if redis_client is not None:
            try:
                cached_books = await redis_client.get(f"favorites:{user.id}:{skip}:{limit}")
                if cached_books:
                    try:
                        books = deserialize_from_json(cached_books)
                        log_info(f"Successfully retrieved {len(books)} favorite books from cache for user {user.email}")
                        return books
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_favorites",
                                "key": f"favorites:{user.id}:{skip}:{limit}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_user_favorites",
                        "key": f"favorites:{user.id}:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        books_service = BookService(db)
        books = await books_service.get_user_favorites(user.id, limit=limit, skip=skip)

        if not books:
            log_info(f"No favorite books found for user {user.email}")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"message": "У вас пока нет книг в избранном"},
            )

        book_responses = [BookResponse.model_validate(book) for book in books]
        log_info(f"Found {len(book_responses)} favorite books for user {user.email}")

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    f"favorites:{user.id}:{skip}:{limit}", serialize_to_json(book_responses), expire=3600  # 1 час
                )
                log_info(f"Successfully cached {len(book_responses)} favorite books for user {user.email}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_favorites",
                        "key": f"favorites:{user.id}:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return book_responses

    except SQLAlchemyError as e:
        log_db_error(
            e,
            {
                "operation": "get_user_favorites",
                "table": "favorites",
                "user_id": str(user.id),
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Ошибка при получении списка избранных книг из базы данных")
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_user_favorites",
                "table": "favorites",
                "user_id": str(user.id),
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Непредвиденная ошибка при получении списка избранных книг")


@router.get("/user/ratings", response_model=List[UserRatingResponse])
async def get_user_ratings(
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    user: User = Depends(current_active_user),
):
    """
    Получить список книг с оценками пользователя.
    """
    try:
        log_info(f"User {user.email} getting rated books")

        # Пытаемся получить оценки из кэша
        if redis_client is not None:
            try:
                cached_ratings = await redis_client.get(f"ratings:{user.id}:{skip}:{limit}")
                if cached_ratings:
                    try:
                        ratings = deserialize_from_json(cached_ratings)
                        log_info(f"Successfully retrieved {len(ratings)} ratings from cache for user {user.email}")
                        return ratings
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_ratings",
                                "key": f"ratings:{user.id}:{skip}:{limit}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_user_ratings",
                        "key": f"ratings:{user.id}:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        books_service = BookService(db)
        books_with_ratings = await books_service.get_user_ratings(user.id, limit=limit, skip=skip)

        if not books_with_ratings:
            log_info(f"No rated books found for user {user.email}")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"message": "У вас пока нет оцененных книг"},
            )

        ratings = [
            UserRatingResponse(book=BookResponse.model_validate(book), user_rating=rating)
            for book, rating in books_with_ratings
        ]
        log_info(f"Found {len(ratings)} rated books for user {user.email}")

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    f"ratings:{user.id}:{skip}:{limit}", serialize_to_json(ratings), expire=3600  # 1 час
                )
                log_info(f"Successfully cached {len(ratings)} ratings for user {user.email}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_ratings",
                        "key": f"ratings:{user.id}:{skip}:{limit}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return ratings

    except SQLAlchemyError as e:
        log_db_error(
            e,
            {
                "operation": "get_user_ratings",
                "table": "ratings",
                "user_id": str(user.id),
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Ошибка при получении списка оцененных книг из базы данных")
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_user_ratings",
                "table": "ratings",
                "user_id": str(user.id),
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise DatabaseException("Непредвиденная ошибка при получении списка оцененных книг")
