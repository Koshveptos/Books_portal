import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from models.user import User
from redis import Redis
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType
from services.recommendation import RecommendationService
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db, get_redis_client
from app.core.exceptions import (
    NotEnoughDataForRecommendationException,
    RecommendationException,
)
from app.core.logger_config import (
    log_cache_error,
    log_db_error,
    log_info,
    log_warning,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


async def get_recommendations_from_db(user_id: int, db: AsyncSession) -> List[BookRecommendation]:
    """Получение рекомендаций из базы данных при недоступности кэша"""
    try:
        recommendation_service = RecommendationService(db, None)
        recommendations = await recommendation_service.get_user_recommendations(
            user_id=user_id,
            limit=10,
            min_rating=3.0,
            min_ratings_count=5,
            recommendation_type=RecommendationType.HYBRID,
            cache=False,
        )
        return recommendations
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_recommendations_from_db",
                "table": "recommendations",
                "user_id": user_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise RecommendationException("Ошибка при получении рекомендаций из базы данных")


@router.get("/", response_model=List[BookRecommendation])
async def get_recommendations(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(2.5, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_ratings_count: int = Query(3, ge=1, le=100, description="Минимальное количество оценок"),
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
    try:
        log_info(
            f"Getting recommendations for user {current_user.id} with type {recommendation_type}, "
            f"limit={limit}, min_rating={min_rating}, use_cache={use_cache}"
        )

        # Пытаемся получить рекомендации из кэша
        if use_cache and redis_client is not None:
            try:
                cached_recommendations = await redis_client.get(f"recommendations:{current_user.id}")
                if cached_recommendations:
                    try:
                        recommendations = json.loads(cached_recommendations)
                        log_info(
                            f"Successfully retrieved {len(recommendations)} recommendations from cache for user {current_user.id}"
                        )
                        return recommendations
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_recommendations",
                                "key": f"recommendations:{current_user.id}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
                        # Если не удалось распарсить кэш, продолжаем с получением из БД
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_recommendations",
                        "key": f"recommendations:{current_user.id}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )
                # Если кэш недоступен, продолжаем с получением из БД

        # Получаем рекомендации из базы данных
        try:
            recommendation_service = RecommendationService(db)
            recommendations = await recommendation_service.get_user_recommendations(
                user_id=current_user.id,
                limit=limit,
                min_rating=min_rating,
                min_ratings_count=min_ratings_count,
                recommendation_type=recommendation_type,
            )

            if not recommendations:
                log_info(f"No recommendations found for user {current_user.id}")
                return []

            log_info(f"Found {len(recommendations)} recommendations for user {current_user.id}")

            # Сохраняем в кэш
            if use_cache and redis_client is not None:
                try:
                    await redis_client.set(
                        f"recommendations:{current_user.id}", json.dumps(recommendations), expire=3600  # 1 час
                    )
                    log_info(f"Successfully cached {len(recommendations)} recommendations for user {current_user.id}")
                except Exception as e:
                    log_cache_error(
                        e,
                        {
                            "operation": "cache_recommendations",
                            "key": f"recommendations:{current_user.id}",
                            "error_type": type(e).__name__,
                            "error_details": str(e),
                        },
                    )
                    # Если не удалось сохранить в кэш, продолжаем без кэширования

            return recommendations

        except NotEnoughDataForRecommendationException as e:
            log_warning(f"Not enough data for recommendations: {str(e)}")
            return []
        except Exception as e:
            log_db_error(
                e,
                {
                    "operation": "get_recommendations",
                    "user_id": current_user.id,
                    "recommendation_type": recommendation_type,
                    "limit": limit,
                    "min_rating": min_rating,
                    "min_ratings_count": min_ratings_count,
                    "use_cache": use_cache,
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )
            # Пытаемся получить популярные книги как запасной вариант
            try:
                log_info(f"Attempting to get popular books as fallback for user {current_user.id}")
                recommendation_service = RecommendationService(db)  # Отключаем кэш для запасного варианта
                recommendations = await recommendation_service._get_popularity_recommendations(
                    limit=limit,
                    min_rating=min_rating,
                    min_ratings_count=min_ratings_count,
                    exclude_book_ids=set(),
                )
                if recommendations:
                    log_info(f"Successfully retrieved {len(recommendations)} popular books as fallback")
                    return recommendations
            except Exception as fallback_error:
                log_db_error(
                    fallback_error,
                    {
                        "operation": "get_popular_recommendations",
                        "table": "recommendations",
                        "user_id": current_user.id,
                        "error_type": type(fallback_error).__name__,
                        "error_details": str(fallback_error),
                    },
                )

            # Если даже запасной вариант не сработал, возвращаем пустой список
            return []

    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_recommendations",
                "table": "recommendations",
                "user_id": current_user.id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        return []


@router.get("/stats", response_model=RecommendationStats)
async def get_recommendation_stats(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
) -> RecommendationStats:
    """Получение статистики рекомендаций для пользователя"""
    try:
        recommendation_service = RecommendationService(db)
        return await recommendation_service.get_recommendation_stats(current_user.id)
    except Exception as e:
        log_db_error(e, {"user_id": current_user.id, "context": "get_recommendation_stats"})
        raise RecommendationException("Ошибка при получении статистики рекомендаций")


@router.get("/similar-users", response_model=List[Dict[str, Any]])
async def get_similar_users(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Получение списка похожих пользователей"""
    try:
        recommendation_service = RecommendationService(db)
        return await recommendation_service._get_similar_users(current_user.id)
    except Exception as e:
        log_db_error(e, {"user_id": current_user.id, "context": "get_similar_users"})
        raise RecommendationException("Ошибка при получении списка похожих пользователей")


@router.get("/author", response_model=List[BookRecommendation])
async def get_author_recommendations(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
) -> List[BookRecommendation]:
    """Получение рекомендаций по авторам"""
    try:
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service._get_author_based_recommendations(
            user_id=current_user.id, limit=10, min_rating=2.5, min_ratings_count=3, exclude_book_ids=set()
        )
        return recommendations
    except Exception as e:
        log_db_error(e, {"user_id": current_user.id, "context": "get_author_recommendations"})
        raise RecommendationException("Ошибка при получении рекомендаций по авторам")


@router.get("/category", response_model=List[BookRecommendation])
async def get_category_recommendations(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
) -> List[BookRecommendation]:
    """Получение рекомендаций по категориям"""
    try:
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service._get_category_based_recommendations(
            user_id=current_user.id, limit=10, min_rating=2.5, min_ratings_count=3, exclude_book_ids=set()
        )
        return recommendations
    except Exception as e:
        log_db_error(e, {"user_id": current_user.id, "context": "get_category_recommendations"})
        raise RecommendationException("Ошибка при получении рекомендаций по категориям")


@router.get("/tag", response_model=List[BookRecommendation])
async def get_tag_recommendations(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
) -> List[BookRecommendation]:
    """Получение рекомендаций по тегам"""
    try:
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service._get_tag_based_recommendations(
            user_id=current_user.id, limit=10, min_rating=2.5, min_ratings_count=3, exclude_book_ids=set()
        )
        return recommendations
    except Exception as e:
        log_db_error(e, {"user_id": current_user.id, "context": "get_tag_recommendations"})
        raise RecommendationException("Ошибка при получении рекомендаций по тегам")
