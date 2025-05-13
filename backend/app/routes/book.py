"""
Маршруты API для книг
"""

from typing import List, Optional

from core.auth import current_active_user, current_moderator
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from models.user import User
from schemas.book import BookCreate, BookResponse, BookSearchResponse, BookUpdate
from services.book import BookService
from sqlalchemy.ext.asyncio import AsyncSession

# Основной роутер для книг
router = APIRouter()

# Маршруты для основных операций с книгами (создание, обновление, удаление)
book_router = APIRouter(prefix="/books", tags=["books"])

# Маршруты для поиска и получения книг
search_router = APIRouter(prefix="/books", tags=["search"])


# Основные операции с книгами
@book_router.post("/", response_model=BookResponse)
async def create_book(
    book_data: BookCreate, current_user: User = Depends(current_moderator), db: AsyncSession = Depends(get_db)
):
    """
    Создать новую книгу (требуются права модератора).

    Требуется Bearer JWT токен авторизации с правами модератора.

    Args:
        book_data: Данные для создания книги
    """
    try:
        service = BookService(db)
        book = await service.create_book(book_data)
        return book
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании книги: {str(e)}")


@book_router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int = Path(..., gt=0),
    current_user: Optional[User] = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить информацию о книге по ID.

    Args:
        book_id: ID книги
    """
    try:
        service = BookService(db)
        user_id = current_user.id if current_user else None
        book = await service.get_book(book_id, user_id)
        if not book:
            raise HTTPException(status_code=404, detail="Книга не найдена")
        return book
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении информации о книге: {str(e)}")


@book_router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_data: BookUpdate,
    book_id: int = Path(..., gt=0),
    current_user: User = Depends(current_moderator),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить информацию о книге (требуются права модератора).

    Требуется Bearer JWT токен авторизации.

    Args:
        book_id: ID книги
        book_data: Данные для обновления
    """
    try:
        service = BookService(db)
        book = await service.update_book(book_id, book_data)
        if not book:
            raise HTTPException(status_code=404, detail="Книга не найдена")
        return book
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении книги: {str(e)}")


@book_router.delete("/{book_id}", response_model=bool)
async def delete_book(
    book_id: int = Path(..., gt=0), current_user: User = Depends(current_moderator), db: AsyncSession = Depends(get_db)
):
    """
    Удалить книгу (требуются права модератора).

    Требуется Bearer JWT токен авторизации.

    Args:
        book_id: ID книги
    """
    try:
        service = BookService(db)
        result = await service.delete_book(book_id)
        if not result:
            raise HTTPException(status_code=404, detail="Книга не найдена")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении книги: {str(e)}")


# Маршруты для поиска книг
@search_router.get("/", response_model=List[BookResponse])
async def get_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    author_id: Optional[int] = None,
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    max_rating: Optional[float] = Query(None, ge=0, le=5),
    min_year: Optional[int] = Query(None, ge=1800),
    max_year: Optional[int] = Query(None, le=2024),
    sort_by: str = Query("rating", regex="^(rating|year|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: Optional[User] = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список книг с фильтрацией и сортировкой.

    Args:
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поисковый запрос
        category_id: ID категории для фильтрации
        author_id: ID автора для фильтрации
        min_rating: Минимальный рейтинг
        max_rating: Максимальный рейтинг
        min_year: Минимальный год издания
        max_year: Максимальный год издания
        sort_by: Поле для сортировки
        sort_order: Порядок сортировки
    """
    try:
        service = BookService(db)
        user_id = current_user.id if current_user else None
        books = await service.get_books(
            skip=skip,
            limit=limit,
            user_id=user_id,
            search=search,
            category_id=category_id,
            author_id=author_id,
            min_rating=min_rating,
            max_year=max_year,
            min_year=min_year,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка книг: {str(e)}")


@search_router.get("/search/", response_model=List[BookSearchResponse])
async def search_books(
    query: str = Query(..., min_length=3, description="Поисковый запрос (минимум 3 символа)"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
    min_ratings_count: int = Query(5, ge=1, description="Минимальное количество оценок"),
    current_user: Optional[User] = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Полнотекстовый поиск книг по названию, описанию или автору.

    Поиск осуществляется по следующим полям:
    - Название книги
    - Описание книги
    - Имя автора

    Результаты сортируются по релевантности и популярности.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        service = BookService(db)
        user_id = current_user.id if current_user else None
        logger.info(f"Searching books with query: {query}, user_id: {user_id}")

        books = await service.search_books(
            query=query, limit=limit, min_ratings_count=min_ratings_count, user_id=user_id
        )
        logger.info(f"Found {len(books)} books matching query: {query}")
        return books
    except Exception as e:
        import traceback

        error_detail = f"Ошибка при поиске книг: {str(e)}"
        logger.error(f"{error_detail}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)


@search_router.get("/by-author/", response_model=List[BookResponse])
async def search_books_by_author(
    author_name: str = Query(..., min_length=3, description="Имя автора (минимум 3 символа)"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
    current_user: Optional[User] = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Поиск книг по имени автора.

    Поиск осуществляется по точному и частичному совпадению имени автора.
    Результаты сортируются по популярности.
    """
    try:
        service = BookService(db)
        user_id = current_user.id if current_user else None
        books = await service.search_books(
            query=author_name,
            limit=limit,
            min_ratings_count=0,  # Отключаем фильтр по количеству оценок
            user_id=user_id,
        )
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске книг по автору: {str(e)}")


@search_router.get("/popular/", response_model=List[BookResponse])
async def get_popular_books(
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество книг"),
    min_ratings_count: int = Query(5, ge=1, description="Минимальное количество оценок"),
    current_user: Optional[User] = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список популярных книг, отсортированных по рейтингу.

    Возвращает книги с количеством оценок не менее указанного,
    отсортированные по среднему рейтингу в порядке убывания.
    """
    try:
        service = BookService(db)
        user_id = current_user.id if current_user else None
        books = await service.get_popular_books(limit=limit, user_id=user_id, min_ratings_count=min_ratings_count)
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении популярных книг: {str(e)}")


@search_router.get("/by-category/{category_id}", response_model=List[BookResponse])
async def search_books_by_category(
    category_id: int = Path(..., gt=0, description="ID категории"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
    current_user: Optional[User] = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Поиск книг по категории.

    Возвращает список книг, относящихся к указанной категории,
    отсортированных по рейтингу в порядке убывания.
    """
    try:
        service = BookService(db)
        user_id = current_user.id if current_user else None
        books = await service.search_books_by_category(category_id=category_id, limit=limit, user_id=user_id)
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске книг по категории: {str(e)}")


@search_router.get("/by-tag/{tag_id}", response_model=List[BookResponse])
async def search_books_by_tag(
    tag_id: int = Path(..., gt=0, description="ID тега"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
    current_user: Optional[User] = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Поиск книг по тегу.

    Возвращает список книг, отмеченных указанным тегом,
    отсортированных по рейтингу в порядке убывания.
    """
    try:
        service = BookService(db)
        user_id = current_user.id if current_user else None
        books = await service.search_books_by_tag(tag_id=tag_id, limit=limit, user_id=user_id)
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске книг по тегу: {str(e)}")


# Подключаем все маршруты к основному роутеру
router.include_router(book_router)  # Основные операции с книгами
router.include_router(search_router)  # Поиск и получение книг
