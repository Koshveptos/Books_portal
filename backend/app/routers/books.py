from datetime import UTC, datetime

from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from models.book import Book, Category, Tag
from schemas.book import BookCreate, BookPartial, BookResponse, BookUpdate, CategoryCreate, TagCreate
from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter()

# @router.get("/{id}")
# def get_book():
#    return {"ну рыбает и хули спотришь":"lol"}
# TODO:
# добавить views для обработки логики, но ток если роутов встанет многовато


@router.get("/", response_model=list[BookResponse])
async def get_books(db: AsyncSession = Depends(get_db)):
    """
    Получить список всех книг.
    """
    try:
        logger.info("Get all books")
        query = select(Book).order_by(Book.id).options(selectinload(Book.categories), selectinload(Book.tags))
        result: Result = await db.execute(query)
        books = result.scalars().all()
        logger.debug("All books got seccessfully")
        return list(books)
    except Exception as e:
        logger.error(f"Interal server error {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получить книгу по её ID.
    """
    try:
        logger.info("Get book by id")
        query = select(Book).options(selectinload(Book.categories), selectinload(Book.tags)).where(Book.id == book_id)
        result = await db.execute(query)
        book = result.scalars().first()
        if book:
            return book
        else:
            logger.error(f"Book with id {book_id} not found")
            raise HTTPException(status_code=404, detail="Book not found")
    except HTTPException:
        # пересылка ошибки что бы все не скатывалось в 500тую
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while creating book: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/", response_model=BookResponse)
async def create_book(book: BookCreate, db: AsyncSession = Depends(get_db)):
    """
    Создать новую книгу.
    """
    try:
        logger.debug(f"Start to create Book: {book.model_dump()}")
        logger.debug("Get Tag and Categories from db")
        # проверка  существования тегов
        tags_id = book.tags
        tags_result = await db.execute(select(Tag).where(Tag.id.in_(tags_id)))
        tags = tags_result.scalars().all()
        if len(tags) != len(tags_id):
            # если есть лишние несуществующие тэги и тд
            missing_tags = set(tags_id) - {t.id for t in tags}
            logger.error(f"Missing some tags: {missing_tags}")
            raise HTTPException(status_code=400, detail=f"Tags with IDs {missing_tags} do not exist")

        categories_id = book.categories
        categories_result = await db.execute(select(Category).where(Category.id.in_(categories_id)))
        categories = categories_result.scalars().all()
        if len(categories) != len(categories_id):
            missing_categories = set(categories_id) - {c.id for c in categories}
            logger.error(f"Missing some categories: {missing_categories}")
            raise HTTPException(status_code=400, detail=f"Categories with IDs {missing_categories} do not exist")

        # Создание книги
        db_book = Book(**book.model_dump(exclude={"categories", "tags"}))
        db_book.tags = tags
        db_book.categories = categories
        db_book.created_at = datetime.now(UTC)
        db_book.updated_at = datetime.now(UTC)

        db.add(db_book)
        await db.commit()
        await db.refresh(db_book)

        # Явная загрузка связанных объектов тк до этго была ленивая и схема давала ошибку
        db_book = await db.get(Book, db_book.id)
        db_book.categories = await db.run_sync(lambda _: db_book.categories)
        db_book.tags = await db.run_sync(lambda _: db_book.tags)
        logger.info(f"Book created successfully with ID: {db_book.id}")
        return db_book
    except HTTPException:
        # пересылка ошибки что бы все не скатывалось в 500тую
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
async def update_book(book_id: int, book_update: BookUpdate, db: AsyncSession = Depends(get_db)):
    """
    Полностью обновить книгу по её ID.
    """
    try:
        logger.info(f"Update informations about book{book_id}")
        query = select(Book).options(selectinload(Book.categories), selectinload(Book.tags)).where(Book.id == book_id)

        result = await db.execute(query)
        book = result.scalars().first()
        if not book:
            logger.error(f"Book with ID {book_id} does not exist")
            raise HTTPException(status_code=404, detail="Book not found")

        for name, value in book_update.model_dump(exclude={"tags", "categories"}).items():
            setattr(book, name, value)
        # обнова категорий
        # про обновление старые тэги и категории будут удалены и заменены на новые
        if book_update.categories:
            categories_result = await db.execute(select(Category).where(Category.id.in_(book_update.categories)))
            categories = categories_result.scalars().all()
            if len(categories) != len(book_update.categories):
                missing_categories = set(book_update.categories) - set(c.id for c in categories)
                logger.error(f"Missing categories{missing_categories}")
                raise HTTPException(status_code=400, detail=f"Categories {missing_categories} not found")
            book.categories = categories
        # обнова тэгов
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
        logger.debug(f"Book with ID { book.id} seccessfully upgrade")
        return book
    except HTTPException:
        # пересылка ошибки что бы все не скатывалось в 500тую
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError while updating book: {str(e)}")
        raise HTTPException(status_code=400, detail="Book data if invalid or already exists")
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while updating books{e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.patch("/{book_id}", response_model=BookResponse)
async def partial_update_book(book_id: int, book_update: BookPartial, db: AsyncSession = Depends(get_db)):
    """
    Частично обновить книгу по её ID.
    """
    try:
        logger.info(f"Partial update book with ID {book_id}")
        query = select(Book).options(selectinload(Book.categories), selectinload(Book.tags)).where(Book.id == book_id)
        result = await db.execute(query)
        book = result.scalars().first()
        if not book:
            logger.error(f"Book with ID {book_id} does not exist")
            raise HTTPException(status_code=404, detail="Book not found")
        # по сути то же самое что и обычное обновление, ток отдельно проверяю все данные и связанные
        update_data = book_update.model_dump(exclude={"tags", "categories"}, exclude_unset=True)
        for name, value in update_data:
            setattr(book, name, value)
        # Обновляем категории, если они указаны в запросе
        if book_update.categories:
            categories_result = await db.execute(select(Category).where(Category.id.in_(book_update.categories)))
            categories = categories_result.scalars().all()
            if len(categories) != len(book_update.categories):
                missing_categories = set(book_update.categories) - set(c.id for c in categories)
                logger.error(f"Missing categories: {missing_categories}")
                raise HTTPException(status_code=400, detail=f"Categories {missing_categories} not found")
            book.categories = categories

        # Обновляем теги, если они указаны в запросе
        if book_update.tags:
            tags_result = await db.execute(select(Tag).where(Tag.id.in_(book_update.tags)))
            tags = tags_result.scalars().all()

            if len(tags) != len(book_update.tags):
                missing_tags = set(book_update.tags) - set(t.id for t in tags)
                logger.error(f"Missing tags: {missing_tags}")
                raise HTTPException(status_code=400, detail=f"Tags {missing_tags} not found")
            book.tags = tags
            await db.commit()
            await db.refresh(book)
            logger.debug(f"Book with ID { book.id} seccessfully upgrade")
            return book
    except HTTPException:
        # пересылка ошибки что бы все не скатывалось в 500тую
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError while updating book: {str(e)}")
        raise HTTPException(status_code=400, detail="Book data if invalid or already exists")
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while updating books{e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/{book_id}", response_model=dict)
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удалить книгу по её ID.
    """
    try:
        book = await db.get(Book, book_id)
        if not book:
            logger.error(f"Book with ID {book_id} nor found")
            raise HTTPException(status_code=404, detail="Book not found")
        await db.delete(book)
        await db.commit()
        logger.debug(f"Book with ID {book_id} successfully deleted")
        return {"message": "Book deleted successfully"}
    except HTTPException:
        # пересылка ошибки что бы все не скатывалось в 500тую
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting Book with ID {book_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/category", response_model=CategoryCreate)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """
    Создать категорию.
    """
    category_db = Category(**category.model_dump())
    db.add(category_db)
    await db.commit()
    await db.refresh(category_db)
    return category_db


@router.post("/tag", response_model=TagCreate)
async def create_tag(tag: TagCreate, db: AsyncSession = Depends(get_db)):
    """
    Создать тег.
    """
    tag_db = Tag(**tag.model_dump())
    db.add(tag_db)
    await db.commit()
    await db.refresh(tag_db)
    return tag_db
