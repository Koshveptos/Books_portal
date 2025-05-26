from auth import current_active_user
from fastapi import APIRouter, Depends, status
from models.book import Author, Book, Category, Tag
from models.user import User
from schemas.book import (
    BookCreate,
    BookPartial,
    BookResponse,
    BookUpdate,
    CategoryCreate,
    CategoryResponse,
    TagCreate,
    TagResponse,
)
from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import (
    BookNotFoundException,
    DatabaseException,
    InvalidBookDataException,
    PermissionDeniedException,
)
from app.core.logger_config import (
    log_db_error,
    log_info,
    log_validation_error,
    log_warning,
)

router = APIRouter()

# Альтернативный роутер для доступа через "плоский" путь /books
books_router = APIRouter()

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

        log_info(f"Successfully retrieved {len(book_responses)} books")
        return book_responses
    except Exception as e:
        log_db_error(e, operation="get_all_books", table="books")
        raise DatabaseException("Ошибка при получении списка книг")


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
    except Exception as e:
        log_db_error(e, operation="get_book", table="books")
        raise DatabaseException("Ошибка при получении книги")


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
            raise InvalidBookDataException(f"Авторы {missing_authors} не найдены")

        # Проверка существования категорий
        categories_result = await db.execute(select(Category).where(Category.id.in_(book.categories)))
        categories = categories_result.scalars().all()
        if len(categories) != len(book.categories):
            missing_categories = set(book.categories) - set(c.id for c in categories)
            log_validation_error(
                ValueError(f"Missing categories: {missing_categories}"), model_name="Book", field="categories"
            )
            raise InvalidBookDataException(f"Категории {missing_categories} не найдены")

        # Проверка существования тегов
        tags_result = await db.execute(select(Tag).where(Tag.id.in_(book.tags)))
        tags = tags_result.scalars().all()
        if len(tags) != len(book.tags):
            missing_tags = set(book.tags) - set(t.id for t in tags)
            log_validation_error(ValueError(f"Missing tags: {missing_tags}"), model_name="Book", field="tags")
            raise InvalidBookDataException(f"Теги {missing_tags} не найдены")

        # Создание объекта книги
        book_dict = book.model_dump(exclude={"authors", "categories", "tags"})
        db_book = Book(**book_dict)
        db_book.authors = authors
        db_book.categories = categories
        db_book.tags = tags

        db.add(db_book)
        await db.commit()
        await db.refresh(db_book)

        log_info(f"Book created successfully with ID: {db_book.id}")

        # Загружаем объект со всеми связями
        result = await db.execute(
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == db_book.id)
        )
        book_with_relations = result.scalar_one()
        return BookResponse.model_validate(book_with_relations)
    except (PermissionDeniedException, InvalidBookDataException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="create_book", table="books")
        raise InvalidBookDataException("Книга с такими данными уже существует")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="create_book", table="books")
        raise DatabaseException("Ошибка при создании книги")


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
                raise InvalidBookDataException(f"Авторы {missing_authors} не найдены")
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
                raise InvalidBookDataException(f"Категории {missing_categories} не найдены")
            book.categories = categories

        # Обновление тегов
        if book_update.tags:
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
        log_db_error(e, operation="update_book", table="books")
        raise InvalidBookDataException("Некорректные данные для обновления книги")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="update_book", table="books")
        raise DatabaseException("Ошибка при обновлении книги")


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
            log_warning(f"User {user.id} attempted to partially update book {book_id} without sufficient permissions")
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

        # Обновление только переданных полей
        update_data = book_update.model_dump(exclude_unset=True)

        # Обновление основных полей
        for name, value in update_data.items():
            if name not in ["authors", "categories", "tags"]:
                setattr(book, name, value)

        # Обновление авторов, если они переданы
        if "authors" in update_data:
            authors_result = await db.execute(select(Author).where(Author.id.in_(update_data["authors"])))
            authors = authors_result.scalars().all()
            if len(authors) != len(update_data["authors"]):
                missing_authors = set(update_data["authors"]) - set(a.id for a in authors)
                log_validation_error(
                    ValueError(f"Missing authors: {missing_authors}"), model_name="Book", field="authors"
                )
                raise InvalidBookDataException(f"Авторы {missing_authors} не найдены")
            book.authors = authors

        # Обновление категорий, если они переданы
        if "categories" in update_data:
            categories_result = await db.execute(select(Category).where(Category.id.in_(update_data["categories"])))
            categories = categories_result.scalars().all()
            if len(categories) != len(update_data["categories"]):
                missing_categories = set(update_data["categories"]) - set(c.id for c in categories)
                log_validation_error(
                    ValueError(f"Missing categories: {missing_categories}"), model_name="Book", field="categories"
                )
                raise InvalidBookDataException(f"Категории {missing_categories} не найдены")
            book.categories = categories

        # Обновление тегов, если они переданы
        if "tags" in update_data:
            tags_result = await db.execute(select(Tag).where(Tag.id.in_(update_data["tags"])))
            tags = tags_result.scalars().all()
            if len(tags) != len(update_data["tags"]):
                missing_tags = set(update_data["tags"]) - set(t.id for t in tags)
                log_validation_error(ValueError(f"Missing tags: {missing_tags}"), model_name="Book", field="tags")
                raise InvalidBookDataException(f"Теги {missing_tags} не найдены")
            book.tags = tags

        await db.commit()
        await db.refresh(book)

        log_info(f"Book {book_id} partially updated successfully")
        return BookResponse.model_validate(book)
    except (PermissionDeniedException, BookNotFoundException, InvalidBookDataException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="partial_update_book", table="books")
        raise InvalidBookDataException("Некорректные данные для обновления книги")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="partial_update_book", table="books")
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
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="delete_book", table="books")
        raise DatabaseException("Ошибка при удалении книги")


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

        log_info(f"Creating new category: {category.name}")

        db_category = Category(**category.model_dump())
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)

        log_info(f"Category created successfully with ID: {db_category.id}")
        return CategoryResponse.model_validate(db_category)
    except PermissionDeniedException:
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="create_category", table="categories")
        raise InvalidBookDataException("Категория с таким названием уже существует")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="create_category", table="categories")
        raise DatabaseException("Ошибка при создании категории")


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

        log_info(f"Creating new tag: {tag.name}")

        db_tag = Tag(**tag.model_dump())
        db.add(db_tag)
        await db.commit()
        await db.refresh(db_tag)

        log_info(f"Tag created successfully with ID: {db_tag.id}")
        return TagResponse.model_validate(db_tag)
    except PermissionDeniedException:
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="create_tag", table="tags")
        raise InvalidBookDataException("Тег с таким названием уже существует")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="create_tag", table="tags")
        raise DatabaseException("Ошибка при создании тега")


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
