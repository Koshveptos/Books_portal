"""
Маршруты API для рекомендаций книг
"""

from typing import List, Optional

from core.auth import current_active_user
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from models.user import User
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType, SimilarUser
from services.recommendation import RecommendationService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[BookRecommendation])
async def get_recommendations(
    limit: int = Query(10, ge=1, le=50),
    recommendation_type: Optional[RecommendationType] = None,
    min_rating: float = Query(3.0, ge=0, le=5),
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить рекомендации книг для пользователя.
    """
    service = RecommendationService(db)
    recommendations = await service.get_user_recommendations(
        user_id=current_user.id,
        limit=limit,
        recommendation_type=recommendation_type or RecommendationType.HYBRID,
        min_rating=min_rating,
        min_year=min_year,
        max_year=max_year,
    )
    return recommendations


@router.get("/stats", response_model=RecommendationStats)
async def get_recommendation_stats(
    current_user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику рекомендаций для пользователя.
    """
    service = RecommendationService(db)
    stats = await service.get_recommendation_stats(current_user.id)
    return stats


@router.get("/books", response_model=List[BookRecommendation])
async def get_book_recommendations(
    limit: int = Query(10, ge=1, le=100),
    min_rating: float = Query(3.0, ge=0.0, le=5.0),
    min_year: Optional[int] = Query(None, ge=1800),
    max_year: Optional[int] = Query(None, le=2024),
    min_ratings_count: int = Query(5, ge=1),
    recommendation_type: RecommendationType = RecommendationType.CONTENT,
    cache: bool = Query(True),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить персональные рекомендации книг.

    Args:
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг книг
        min_year: Минимальный год издания
        max_year: Максимальный год издания
        min_ratings_count: Минимальное количество оценок
        recommendation_type: Тип рекомендаций
        cache: Использовать кэширование
    """
    try:
        service = RecommendationService(db)
        recommendations = await service.get_user_recommendations(
            user_id=current_user.id,
            limit=limit,
            min_rating=min_rating,
            min_year=min_year,
            max_year=max_year,
            min_ratings_count=min_ratings_count,
            recommendation_type=recommendation_type,
            cache=cache,
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении рекомендаций: {str(e)}")


@router.get("/similar-users", response_model=List[SimilarUser])
async def get_similar_users(
    limit: int = Query(10, ge=1, le=100),
    min_common_ratings: int = Query(3, ge=1),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список похожих пользователей.

    Args:
        limit: Максимальное количество пользователей
        min_common_ratings: Минимальное количество общих оценок
    """
    try:
        service = RecommendationService(db)
        similar_users = await service._get_similar_users(user_id=current_user.id, min_common_ratings=min_common_ratings)
        return similar_users[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении похожих пользователей: {str(e)}")


@router.get("/authors/{author_id}", response_model=List[BookRecommendation])
async def get_author_recommendations(
    author_id: int = Path(..., gt=0),
    limit: int = Query(10, ge=1, le=100),
    min_rating: float = Query(3.0, ge=0.0, le=5.0),
    min_year: Optional[int] = Query(None, ge=1800),
    max_year: Optional[int] = Query(None, le=2024),
    min_ratings_count: int = Query(5, ge=1),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить рекомендации книг по автору.

    Args:
        author_id: ID автора
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг книг
        min_year: Минимальный год издания
        max_year: Максимальный год издания
        min_ratings_count: Минимальное количество оценок
    """
    try:
        service = RecommendationService(db)
        recommendations = await service.get_user_recommendations(
            user_id=current_user.id,
            limit=limit,
            min_rating=min_rating,
            min_year=min_year,
            max_year=max_year,
            min_ratings_count=min_ratings_count,
            recommendation_type=RecommendationType.AUTHOR,
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении рекомендаций по автору: {str(e)}")


@router.get("/categories/{category_id}", response_model=List[BookRecommendation])
async def get_category_recommendations(
    category_id: int = Path(..., gt=0),
    limit: int = Query(10, ge=1, le=100),
    min_rating: float = Query(3.0, ge=0.0, le=5.0),
    min_year: Optional[int] = Query(None, ge=1800),
    max_year: Optional[int] = Query(None, le=2024),
    min_ratings_count: int = Query(5, ge=1),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить рекомендации книг по категории.

    Args:
        category_id: ID категории
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг книг
        min_year: Минимальный год издания
        max_year: Максимальный год издания
        min_ratings_count: Минимальное количество оценок
    """
    try:
        service = RecommendationService(db)
        recommendations = await service.get_user_recommendations(
            user_id=current_user.id,
            limit=limit,
            min_rating=min_rating,
            min_year=min_year,
            max_year=max_year,
            min_ratings_count=min_ratings_count,
            recommendation_type=RecommendationType.CATEGORY,
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении рекомендаций по категории: {str(e)}")


@router.get("/tags/{tag_id}", response_model=List[BookRecommendation])
async def get_tag_recommendations(
    tag_id: int = Path(..., gt=0),
    limit: int = Query(10, ge=1, le=100),
    min_rating: float = Query(3.0, ge=0.0, le=5.0),
    min_year: Optional[int] = Query(None, ge=1800),
    max_year: Optional[int] = Query(None, le=2024),
    min_ratings_count: int = Query(5, ge=1),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить рекомендации книг по тегу.

    Args:
        tag_id: ID тега
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг книг
        min_year: Минимальный год издания
        max_year: Максимальный год издания
        min_ratings_count: Минимальное количество оценок
    """
    try:
        service = RecommendationService(db)
        recommendations = await service.get_user_recommendations(
            user_id=current_user.id,
            limit=limit,
            min_rating=min_rating,
            min_year=min_year,
            max_year=max_year,
            min_ratings_count=min_ratings_count,
            recommendation_type=RecommendationType.TAG,
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении рекомендаций по тегу: {str(e)}")
