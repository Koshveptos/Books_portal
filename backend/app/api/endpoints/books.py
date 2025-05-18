from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.book import BookResponse
from app.services.book import BookService

router = APIRouter()


@router.get("/category/{category_id}", response_model=List[BookResponse])
async def get_books_by_category(
    category_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    min_year: Optional[int] = Query(None, ge=1800),
    max_year: Optional[int] = Query(None, le=2100),
    sort_by: str = Query("rating", regex="^(rating|year|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """
    Получить список книг определенной категории с фильтрацией и сортировкой.

    - **category_id**: ID категории
    - **skip**: Количество пропускаемых записей
    - **limit**: Максимальное количество записей
    - **min_rating**: Минимальный рейтинг (0-5)
    - **min_year**: Минимальный год издания
    - **max_year**: Максимальный год издания
    - **sort_by**: Поле для сортировки (rating/year/title)
    - **sort_order**: Порядок сортировки (asc/desc)
    """
    book_service = BookService(db)
    books = await book_service.get_books(
        skip=skip,
        limit=limit,
        category_id=category_id,
        min_rating=min_rating,
        min_year=min_year,
        max_year=max_year,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return books


@router.get("/author/{author_id}", response_model=List[BookResponse])
def get_books_by_author(author_id: int, db: Session = Depends(get_db)):
    """Получить все книги определенного автора"""
    book_service = BookService(db)
    books = book_service.get_books_by_author(author_id)
    return books


@router.get("/tag/{tag_id}", response_model=List[BookResponse])
def get_books_by_tag(tag_id: int, db: Session = Depends(get_db)):
    """Получить все книги с определенным тегом"""
    book_service = BookService(db)
    books = book_service.get_books_by_tag(tag_id)
    return books


@router.get("/search", response_model=List[BookResponse])
def search_books(query: str, db: Session = Depends(get_db)):
    """Поиск книг по названию, описанию или автору"""
    book_service = BookService(db)
    books = book_service.search_books(query)
    return books


# ... остальные эндпоинты ...
