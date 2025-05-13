from typing import List, Optional

from core.dependencies import get_current_active_user
from dependencies import get_db
from fastapi import APIRouter, Depends, Query
from models.user import User
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType, SimilarUser
from services.recommendations import RecommendationService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/", response_model=List[BookRecommendation])
async def get_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(3.0, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_year: Optional[int] = Query(None, description="Минимальный год издания"),
    max_year: Optional[int] = Query(None, description="Максимальный год издания"),
    min_ratings_count: int = Query(5, ge=1, le=100, description="Минимальное количество оценок"),
    recommendation_type: RecommendationType = Query(RecommendationType.HYBRID, description="Тип рекомендаций"),
    use_cache: bool = Query(True, description="Использовать кэширование"),
):
    """
    Получить персональные рекомендации книг.

    Этот эндпоинт возвращает список книг, которые могут понравиться пользователю,
    основываясь на его предыдущих оценках, лайках и предпочтениях.

    В зависимости от выбранного типа рекомендаций, система будет использовать
    различные алгоритмы для подбора книг:
    - hybrid: комбинирует все стратегии
    - collaborative: на основе оценок похожих пользователей
    - content: на основе интересов пользователя (авторы, категории, теги)
    - popularity: популярные книги с высоким рейтингом
    - author: книги от любимых авторов
    - category: книги в любимых категориях
    - tag: книги с любимыми тегами
    """
    recommendation_service = RecommendationService(db)
    recommendations = await recommendation_service.get_user_recommendations(
        user_id=current_user.id,
        limit=limit,
        min_rating=min_rating,
        min_year=min_year,
        max_year=max_year,
        min_ratings_count=min_ratings_count,
        recommendation_type=recommendation_type,
        cache=use_cache,
    )
    return recommendations


@router.get("/stats", response_model=RecommendationStats)
async def get_recommendation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить статистику для персональных рекомендаций.

    Возвращает информацию о предпочтениях пользователя, количестве оцененных книг,
    любимых авторах, категориях и тегах, а также готовности системы
    предоставлять различные типы рекомендаций для этого пользователя.
    """
    recommendation_service = RecommendationService(db)
    stats = await recommendation_service.get_recommendation_stats(user_id=current_user.id)
    return stats


@router.get("/similar-users", response_model=List[SimilarUser])
async def get_similar_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество похожих пользователей"),
    min_common_ratings: int = Query(
        3, ge=1, le=20, description="Минимальное количество общих оценок для определения сходства"
    ),
):
    """
    Получить список пользователей с похожими предпочтениями.

    Этот эндпоинт находит пользователей с похожими вкусами на основе
    оценок книг. Используется для коллаборативной фильтрации и
    помогает пользователям найти единомышленников.
    """
    recommendation_service = RecommendationService(db)
    similar_users = await recommendation_service.get_similar_users(
        user_id=current_user.id, limit=limit, min_common_ratings=min_common_ratings
    )
    return similar_users


@router.get("/by-author", response_model=List[BookRecommendation])
async def get_author_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(3.0, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_year: Optional[int] = Query(None, description="Минимальный год издания"),
    max_year: Optional[int] = Query(None, description="Максимальный год издания"),
    min_ratings_count: int = Query(5, ge=1, le=100, description="Минимальное количество оценок"),
):
    """
    Получить рекомендации книг от любимых авторов.

    Этот эндпоинт анализирует оценки пользователя, определяет
    любимых авторов и рекомендует непрочитанные книги этих авторов.
    """
    recommendation_service = RecommendationService(db)
    user_preferences = await recommendation_service._get_user_preferences(current_user.id)
    recommendations = await recommendation_service._get_author_recommendations(
        user_preferences=user_preferences,
        limit=limit,
        min_rating=min_rating,
        min_year=min_year,
        max_year=max_year,
        min_ratings_count=min_ratings_count,
        user_id=current_user.id,
    )
    return recommendations


@router.get("/by-category", response_model=List[BookRecommendation])
async def get_category_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(3.0, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_year: Optional[int] = Query(None, description="Минимальный год издания"),
    max_year: Optional[int] = Query(None, description="Максимальный год издания"),
    min_ratings_count: int = Query(5, ge=1, le=100, description="Минимальное количество оценок"),
):
    """
    Получить рекомендации книг из любимых категорий.

    Этот эндпоинт анализирует оценки пользователя, определяет
    любимые категории и рекомендует непрочитанные книги из этих категорий.
    """
    recommendation_service = RecommendationService(db)
    user_preferences = await recommendation_service._get_user_preferences(current_user.id)
    recommendations = await recommendation_service._get_category_recommendations(
        user_preferences=user_preferences,
        limit=limit,
        min_rating=min_rating,
        min_year=min_year,
        max_year=max_year,
        min_ratings_count=min_ratings_count,
        user_id=current_user.id,
    )
    return recommendations


@router.get("/by-tag", response_model=List[BookRecommendation])
async def get_tag_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(3.0, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_year: Optional[int] = Query(None, description="Минимальный год издания"),
    max_year: Optional[int] = Query(None, description="Максимальный год издания"),
    min_ratings_count: int = Query(5, ge=1, le=100, description="Минимальное количество оценок"),
):
    """
    Получить рекомендации книг с любимыми тегами.

    Этот эндпоинт анализирует оценки пользователя, определяет
    любимые теги и рекомендует непрочитанные книги с этими тегами.
    """
    recommendation_service = RecommendationService(db)
    user_preferences = await recommendation_service._get_user_preferences(current_user.id)
    recommendations = await recommendation_service._get_tag_recommendations(
        user_preferences=user_preferences,
        limit=limit,
        min_rating=min_rating,
        min_year=min_year,
        max_year=max_year,
        min_ratings_count=min_ratings_count,
        user_id=current_user.id,
    )
    return recommendations
