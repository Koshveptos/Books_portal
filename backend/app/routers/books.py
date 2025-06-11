from typing import List

from auth import current_active_user
from fastapi import APIRouter, Depends, Query, status
from models.book import Author, Book, Category, Tag
from models.user import User
from schemas.book import (
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
from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import (
    AuthorNotFoundException,
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
    log_db_error,
    log_info,
    log_validation_error,
    log_warning,
)
from app.services.book import BookService

router = APIRouter(tags=["books"])
books_router = APIRouter(tags=["books"])

# Маршруты поиска и обновления векторов перенесены в routers/search.py


@router.get("/", response_model=list[BookResponse])
async def get_books(
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список всех книг. Публичный эндпоинт.
    """
    try:
        log_info("Getting all books")
        query = (
            select(Book)
            .order_by(Book.id)
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
                log_db_error(e, operation="get_books_validation", table="books", book_id=str(book.id))
                continue  # Пропускаем книгу с ошибкой валидации

        log_info(f"Successfully retrieved {len(book_responses)} books")
        return book_responses
    except SQLAlchemyError as e:
        log_db_error(e, operation="get_all_books", table="books")
        raise DatabaseException("Ошибка при получении списка книг из базы данных")
    except Exception as e:
        log_db_error(e, operation="get_all_books", table="books")
        raise DatabaseException("Непредвиденная ошибка при получении списка книг")


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить книгу по её ID. Публичный эндпоинт.
    """
    try:
        log_info(f"Getting book with ID: {book_id}")
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

        log_info(f"Successfully retrieved book with ID: {book_id}")
        return BookResponse.model_validate(book)
    except BookNotFoundException:
        raise
    except SQLAlchemyError as e:
        log_db_error(e, operation="get_book", table="books", book_id=str(book_id))
        raise DatabaseException("Ошибка при получении книги из базы данных")
    except Exception as e:
        log_db_error(e, operation="get_book", table="books", book_id=str(book_id))
        raise DatabaseException("Непредвиденная ошибка при получении книги")


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


@router.get("/by-author/{author_id}", response_model=list[BookResponse])
async def get_books_by_author(
    author_id: int,
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список книг по автору.

    Args:
        author_id: ID автора
        limit: Максимальное количество результатов
    """
    try:
        log_info(f"Getting books by author ID: {author_id}")

        # Проверяем существование автора
        author = await db.execute(select(Author).where(Author.id == author_id))
        if not author.scalar_one_or_none():
            log_warning(f"Author with ID {author_id} not found")
            raise AuthorNotFoundException(f"Автор с ID {author_id} не найден")

        books_service = BookService(db)
        books = await books_service.get_books(author_id=author_id, limit=limit)

        if not books:
            log_info(f"No books found for author ID: {author_id}")
            return []

        log_info(f"Found {len(books)} books for author ID: {author_id}")
        return [BookResponse.model_validate(book) for book in books]

    except AuthorNotFoundException:
        raise
    except SQLAlchemyError as e:
        log_db_error(e, operation="get_books_by_author", table="books", author_id=str(author_id))
        raise DatabaseException("Ошибка при получении книг по автору")
    except Exception as e:
        log_db_error(e, operation="get_books_by_author", table="books", author_id=str(author_id))
        raise DatabaseException("Непредвиденная ошибка при получении книг по автору")


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Получить список всех категорий.
    """
    try:
        log_info(f"User {user.email} getting all categories")

        query = select(Category).order_by(Category.name_categories)
        result = await db.execute(query)
        categories = result.scalars().all()

        log_info(f"Found {len(categories)} categories")
        return [CategoryResponse.model_validate(category) for category in categories]

    except Exception as e:
        log_db_error(e, operation="get_categories")
        raise DatabaseException("Ошибка при получении списка категорий")


@router.get("/authors", response_model=List[AuthorResponse])
async def get_authors(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Получить список всех авторов.
    """
    try:
        log_info(f"User {user.email} getting all authors")

        query = select(Author).order_by(Author.name)
        result = await db.execute(query)
        authors = result.scalars().all()

        log_info(f"Found {len(authors)} authors")
        return [AuthorResponse.model_validate(author) for author in authors]

    except Exception as e:
        log_db_error(e, operation="get_authors")
        raise DatabaseException("Ошибка при получении списка авторов")


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
    user: User = Depends(current_active_user),
):
    """
    Получить список книг в избранном пользователя.
    """
    try:
        log_info(f"User {user.email} getting favorite books")

        books_service = BookService(db)
        books = await books_service.get_user_favorites(user.id, limit=limit, skip=skip)

        if not books:
            log_info(f"No favorite books found for user {user.email}")
            return []

        log_info(f"Found {len(books)} favorite books for user {user.email}")
        return [BookResponse.model_validate(book) for book in books]

    except SQLAlchemyError as e:
        log_db_error(e, operation="get_user_favorites", table="favorites", user_id=str(user.id))
        raise DatabaseException("Ошибка при получении списка избранных книг из базы данных")
    except Exception as e:
        log_db_error(e, operation="get_user_favorites", table="favorites", user_id=str(user.id))
        raise DatabaseException("Непредвиденная ошибка при получении списка избранных книг")


@router.get("/user/ratings", response_model=List[UserRatingResponse])
async def get_user_ratings(
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Получить список книг с оценками пользователя.
    """
    try:
        log_info(f"User {user.email} getting rated books")

        books_service = BookService(db)
        books_with_ratings = await books_service.get_user_ratings(user.id, limit=limit, skip=skip)

        if not books_with_ratings:
            log_info(f"No rated books found for user {user.email}")
            return []

        log_info(f"Found {len(books_with_ratings)} rated books for user {user.email}")
        return [
            UserRatingResponse(book=BookResponse.model_validate(book), user_rating=rating)
            for book, rating in books_with_ratings
        ]

    except SQLAlchemyError as e:
        log_db_error(e, operation="get_user_ratings", table="ratings", user_id=str(user.id))
        raise DatabaseException("Ошибка при получении списка оцененных книг из базы данных")
    except Exception as e:
        log_db_error(e, operation="get_user_ratings", table="ratings", user_id=str(user.id))
        raise DatabaseException("Непредвиденная ошибка при получении списка оцененных книг")
