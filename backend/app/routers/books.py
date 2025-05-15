from auth import current_active_user
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
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
        logger.info("Get all books")
        query = (
            select(Book)
            .order_by(Book.id)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
        )
        result: Result = await db.execute(query)
        books = result.scalars().all()
        logger.debug("All books got successfully")

        # Преобразуем книги в модели Pydantic, проверяя, что все связи загружены
        book_responses = []
        for book in books:
            # Проверяем, что связи загружены корректно
            if not (hasattr(book, "authors") and hasattr(book, "categories") and hasattr(book, "tags")):
                # Если связи не загружены, загружаем их явно
                book_id = book.id
                query = (
                    select(Book)
                    .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
                    .where(Book.id == book_id)
                )
                result = await db.execute(query)
                book = result.scalar_one()

            book_responses.append(BookResponse.model_validate(book))

        return book_responses
    except Exception as e:
        logger.error(f"Internal server error {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить книгу по её ID. Публичный эндпоинт.
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
            return BookResponse.model_validate(book)
        else:
            logger.error(f"Book with id {book_id} not found")
            raise HTTPException(status_code=404, detail="Book not found")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while getting book: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


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
        logger.info(f"Creating new book: {book.title}")
        logger.debug(f"Received book data for creation (raw from Pydantic model): {book!r}")
        logger.debug(f"Language from Pydantic model before ORM: {book.language} (type: {type(book.language)})")

        # Проверка существования авторов
        authors_result = await db.execute(select(Author).where(Author.id.in_(book.authors)))
        authors = authors_result.scalars().all()
        if len(authors) != len(book.authors):
            missing_authors = set(book.authors) - set(a.id for a in authors)
            logger.error(f"Missing authors: {missing_authors}")
            raise HTTPException(status_code=400, detail=f"Authors {missing_authors} not found")

        # Проверка существования категорий
        categories_result = await db.execute(select(Category).where(Category.id.in_(book.categories)))
        categories = categories_result.scalars().all()
        if len(categories) != len(book.categories):
            missing_categories = set(book.categories) - set(c.id for c in categories)
            logger.error(f"Missing categories: {missing_categories}")
            raise HTTPException(status_code=400, detail=f"Categories {missing_categories} not found")

        # Проверка существования тегов
        tags_result = await db.execute(select(Tag).where(Tag.id.in_(book.tags)))
        tags = tags_result.scalars().all()
        if len(tags) != len(book.tags):
            missing_tags = set(book.tags) - set(t.id for t in tags)
            logger.error(f"Missing tags: {missing_tags}")
            raise HTTPException(status_code=400, detail=f"Tags {missing_tags} not found")

        # Создание объекта книги
        book_dict = book.model_dump(exclude={"authors", "categories", "tags"})
        db_book = Book(**book_dict)
        db_book.authors = authors
        db_book.categories = categories
        db_book.tags = tags

        db.add(db_book)
        await db.commit()
        await db.refresh(db_book)

        logger.info(f"Book created successfully with ID: {db_book.id}")

        # Вместо прямой валидации загружаем объект со всеми связями
        result = await db.execute(
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == db_book.id)
        )
        book_with_relations = result.scalar_one()
        return BookResponse.model_validate(book_with_relations)
    except HTTPException:
        # Пробрасываем уже созданные HTTP исключения
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError while creating book: {str(e)}")
        raise HTTPException(status_code=400, detail="Book data is invalid or already exists")
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
        # Явно загружаем связи и возвращаем Pydantic-схему
        result = await db.execute(
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == book.id)
        )
        book_with_relations = result.scalar_one()
        return BookResponse.model_validate(book_with_relations)
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
        logger.debug(f"Book with ID {book.id} successfully partially updated")

        # Явно загружаем связи и возвращаем Pydantic-схему
        result = await db.execute(
            select(Book)
            .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
            .where(Book.id == book.id)
        )
        book_with_relations = result.scalar_one()
        return BookResponse.model_validate(book_with_relations)

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError while partially updating book: {str(e)}")
        raise HTTPException(status_code=400, detail="Book data is invalid or already exists")
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while partially updating book: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(current_active_user)):
    """
    Удалить книгу по её ID.
    """
    if not user.is_superuser and not user.is_moderator:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        logger.info(f"Deleting book with ID {book_id}")
        query = select(Book).where(Book.id == book_id)
        result = await db.execute(query)
        book = result.scalars().first()

        if not book:
            logger.error(f"Book with ID {book_id} not found")
            raise HTTPException(status_code=404, detail="Book not found")

        await db.delete(book)
        await db.commit()

        logger.info(f"Book with ID {book_id} successfully deleted")
        return None

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while deleting book: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/category", response_model=CategoryResponse)
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
    try:
        logger.info(f"Создание новой категории: {category.name_categories}")

        # Проверка на дубликаты
        stmt = select(Category).where(Category.name_categories == category.name_categories)
        result = await db.execute(stmt)
        existing_category = result.scalars().first()

        if existing_category:
            logger.warning(f"Попытка создать дублирующуюся категорию: {category.name_categories}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Категория с именем '{category.name_categories}' уже существует",
            )

        category_db = Category(**category.model_dump())
        db.add(category_db)
        await db.commit()
        await db.refresh(category_db)

        logger.info(f"Категория успешно создана с ID: {category_db.id}")
        return category_db
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Ошибка целостности при создании категории: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Категория '{category.name_categories}' уже существует")
    except Exception as e:
        await db.rollback()
        logger.error(f"Непредвиденная ошибка при создании категории: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/tag", response_model=TagResponse)
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
    try:
        logger.info(f"Создание нового тега: {tag.name_tag}")

        # Проверка на дубликаты
        stmt = select(Tag).where(Tag.name_tag == tag.name_tag)
        result = await db.execute(stmt)
        existing_tag = result.scalars().first()

        if existing_tag:
            logger.warning(f"Попытка создать дублирующийся тег: {tag.name_tag}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"Тег с именем '{tag.name_tag}' уже существует"
            )

        tag_db = Tag(**tag.model_dump())
        db.add(tag_db)
        await db.commit()
        await db.refresh(tag_db)

        logger.info(f"Тег успешно создан с ID: {tag_db.id}")
        return tag_db
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Ошибка целостности при создании тега: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Тег '{tag.name_tag}' уже существует")
    except Exception as e:
        await db.rollback()
        logger.error(f"Непредвиденная ошибка при создании тега: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


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
