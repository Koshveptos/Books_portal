"""
Маршруты API для взаимодействий пользователей с книгами (оценки, лайки, избранное)
"""

from typing import List, Optional

from core.auth import current_active_user
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from models.user import User
from schemas.interactions import FavoriteResponse, LikeResponse, RatingCreate, RatingResponse
from services.interactions import InteractionsService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["interactions"])


@router.post("/ratings", response_model=RatingResponse)
async def create_rating(
    rating: RatingCreate, current_user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    Создать или обновить оценку книги.
    """
    service = InteractionsService(db)
    return await service.create_rating(current_user.id, rating)


@router.get("/ratings", response_model=List[RatingResponse])
async def get_user_ratings(
    book_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить оценки текущего пользователя.
    """
    service = InteractionsService(db)
    return await service.get_user_ratings(current_user.id, book_id, skip, limit)


@router.get("/ratings/book/{book_id}", response_model=List[RatingResponse])
async def get_book_ratings(
    book_id: int, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db: AsyncSession = Depends(get_db)
):
    """
    Получить оценки книги.
    """
    service = InteractionsService(db)
    return await service.get_book_ratings(book_id, skip, limit)


@router.delete("/ratings/{rating_id}", response_model=bool)
async def delete_rating(
    rating_id: int, current_user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    Удалить оценку.
    """
    service = InteractionsService(db)
    result = await service.delete_rating(rating_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Оценка не найдена или не принадлежит пользователю")
    return result


@router.post("/like/{book_id}", response_model=LikeResponse)
async def like_book(
    book_id: int, current_user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    Поставить лайк книге.
    """
    service = InteractionsService(db)
    return await service.like_book(current_user.id, book_id)


@router.delete("/like/{book_id}", response_model=bool)
async def unlike_book(
    book_id: int, current_user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    Убрать лайк с книги.
    """
    service = InteractionsService(db)
    result = await service.unlike_book(current_user.id, book_id)
    if not result:
        raise HTTPException(status_code=404, detail="Лайк не найден")
    return result


@router.post("/favorite/{book_id}", response_model=FavoriteResponse)
async def add_to_favorites(
    book_id: int, current_user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    Добавить книгу в избранное.
    """
    service = InteractionsService(db)
    return await service.add_to_favorites(current_user.id, book_id)


@router.delete("/favorite/{book_id}", response_model=bool)
async def remove_from_favorites(
    book_id: int, current_user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    Удалить книгу из избранного.
    """
    service = InteractionsService(db)
    result = await service.remove_from_favorites(current_user.id, book_id)
    if not result:
        raise HTTPException(status_code=404, detail="Книга не найдена в избранном")
    return result
