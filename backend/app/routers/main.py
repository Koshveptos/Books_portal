from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from models.book import Book
from schemas.book import BookResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["main"])


@router.get("/", response_model=list[BookResponse])
async def get_home_page(db: AsyncSession = Depends(get_db), limit: int = 10):
    """
    Получить книги для главной страницы (популярные и новые)
    """
    try:
        # Получаем популярные книги
        popular_query = select(Book).order_by(Book.ratings_count.desc()).limit(limit)
        popular_result = await db.execute(popular_query)
        popular_books = popular_result.scalars().all()

        # Получаем новые книги
        new_query = select(Book).order_by(Book.created_at.desc()).limit(limit)
        new_result = await db.execute(new_query)
        new_books = new_result.scalars().all()

        # Объединяем результаты
        all_books = list(set(popular_books + new_books))

        return [BookResponse.model_validate(book) for book in all_books]
    except Exception as e:
        logger.error(f"Error getting home page data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
