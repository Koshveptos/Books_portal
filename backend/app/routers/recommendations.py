from typing import List, Optional

from core.dependencies import get_current_active_user, get_db, get_redis_client
from core.logger_config import logger
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from models.user import User
from redis import Redis
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType, SimilarUser
from services.recommendations import RecommendationService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/", response_model=List[BookRecommendation])
async def get_recommendations(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
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
    """
    try:
        recommendation_service = RecommendationService(db, redis_client)
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

        if not recommendations:
            logger.info(f"No recommendations found for user {current_user.id}")
            return Response(status_code=status.HTTP_204_NO_CONTENT)  # Пустой ответ

        logger.debug(f"Returning {len(recommendations)} recommendations for user {current_user.id}")
        return recommendations

    except Exception as e:
        logger.error(f"Error fetching recommendations for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении рекомендаций",
        )


@router.get("/stats", response_model=RecommendationStats)
async def get_recommendation_stats(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить статистику для персональных рекомендаций.
    """
    try:
        recommendation_service = RecommendationService(db, redis_client)
        stats = await recommendation_service.get_recommendation_stats(user_id=current_user.id)
        logger.debug(f"Returning recommendation stats for user {current_user.id}")
        return stats

    except Exception as e:
        logger.error(f"Error fetching recommendation stats for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики рекомендаций",
        )


@router.get("/similar-users", response_model=List[SimilarUser])
async def get_similar_users(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество похожих пользователей"),
    min_common_ratings: int = Query(
        3, ge=1, le=20, description="Минимальное количество общих оценок для определения сходства"
    ),
):
    """
    Получить список пользователей с похожими предпочтениями.
    """
    try:
        recommendation_service = RecommendationService(db, redis_client)
        similar_users = await recommendation_service.get_similar_users(
            user_id=current_user.id, limit=limit, min_common_ratings=min_common_ratings
        )

        if not similar_users:
            logger.info(f"No similar users found for user {current_user.id}")
            return Response(status_code=status.HTTP_204_NO_CONTENT)  # Пустой ответ

        logger.debug(f"Returning {len(similar_users)} similar users for user {current_user.id}")
        return similar_users

    except Exception as e:
        logger.error(f"Error fetching similar users for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при поиске похожих пользователей",
        )


@router.get("/by-author", response_model=List[BookRecommendation])
async def get_author_recommendations(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(3.0, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_year: Optional[int] = Query(None, description="Минимальный год издания"),
    max_year: Optional[int] = Query(None, description="Максимальный год издания"),
    min_ratings_count: int = Query(5, ge=1, le=100, description="Минимальное количество оценок"),
):
    """
    Получить рекомендации книг от любимых авторов.
    """
    try:
        recommendation_service = RecommendationService(db, redis_client)
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

        if not recommendations:
            logger.info(f"No author recommendations found for user {current_user.id}")
            return Response(status_code=status.HTTP_204_NO_CONTENT)  # Пустой ответ

        logger.debug(f"Returning {len(recommendations)} author recommendations for user {current_user.id}")
        return recommendations

    except Exception as e:
        logger.error(f"Error fetching author recommendations for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении рекомендаций по авторам",
        )


@router.get("/by-category", response_model=List[BookRecommendation])
async def get_category_recommendations(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(3.0, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_year: Optional[int] = Query(None, description="Минимальный год издания"),
    max_year: Optional[int] = Query(None, description="Максимальный год издания"),
    min_ratings_count: int = Query(5, ge=1, le=100, description="Минимальное количество оценок"),
):
    """
    Получить рекомендации книг из любимых категорий.
    """
    try:
        recommendation_service = RecommendationService(db, redis_client)
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

        if not recommendations:
            logger.info(f"No category recommendations found for user {current_user.id}")
            return Response(status_code=status.HTTP_204_NO_CONTENT)  # Пустой ответ

        logger.debug(f"Returning {len(recommendations)} category recommendations for user {current_user.id}")
        return recommendations

    except Exception as e:
        logger.error(f"Error fetching category recommendations for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении рекомендаций по категориям",
        )


@router.get("/by-tag", response_model=List[BookRecommendation])
async def get_tag_recommendations(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(3.0, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_year: Optional[int] = Query(None, description="Минимальный год издания"),
    max_year: Optional[int] = Query(None, description="Максимальный год издания"),
    min_ratings_count: int = Query(5, ge=1, le=100, description="Минимальное количество оценок"),
):
    """
    Получить рекомендации книг с любимыми тегами.
    """
    try:
        recommendation_service = RecommendationService(db, redis_client)
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

        if not recommendations:
            logger.info(f"No tag recommendations found for user {current_user.id}")
            return Response(status_code=status.HTTP_204_NO_CONTENT)  # Пустой ответ

        logger.debug(f"Returning {len(recommendations)} tag recommendations for user {current_user.id}")
        return recommendations

    except Exception as e:
        logger.error(f"Error fetching tag recommendations for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении рекомендаций по тегам",
        )
