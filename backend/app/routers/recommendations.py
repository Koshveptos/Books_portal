import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.user import User
from redis.asyncio import Redis
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType
from services.recommendation import RecommendationService
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db, get_redis_client
from app.core.exceptions import (
    RecommendationException,
)
from app.core.logger_config import (
    log_cache_error,
    log_db_error,
    log_info,
)
from app.utils.json_serializer import deserialize_from_json, serialize_to_json

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


async def get_recommendations_from_db(user_id: int, db: AsyncSession) -> List[BookRecommendation]:
    """Получение рекомендаций из базы данных при недоступности кэша"""
    try:
        recommendation_service = RecommendationService(db)
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
    redis_client: Optional[Redis] = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(2.5, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_ratings_count: int = Query(3, ge=1, le=100, description="Минимальное количество оценок"),
    recommendation_type: RecommendationType = Query(RecommendationType.HYBRID, description="Тип рекомендаций"),
    use_cache: bool = Query(True, description="Использовать кэширование"),
):
    """
    Получить персональные рекомендации книг для пользователя.

    Args:
        db: Сессия базы данных
        redis_client: Клиент Redis
        current_user: Текущий пользователь
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг книг
        min_ratings_count: Минимальное количество оценок
        recommendation_type: Тип рекомендаций
        use_cache: Использовать кэширование

    Returns:
        List[BookRecommendation]: Список рекомендованных книг
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
                        recommendations_data = deserialize_from_json(cached_recommendations)
                        log_info(
                            f"Successfully retrieved {len(recommendations_data)} recommendations from cache for user {current_user.id}"
                        )
                        return [BookRecommendation(**rec) for rec in recommendations_data]
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

        # Получаем рекомендации из базы данных
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_user_recommendations(
            user_id=current_user.id,
            limit=limit,
            min_rating=min_rating,
            min_ratings_count=min_ratings_count,
            recommendation_type=recommendation_type,
            cache=use_cache,
        )

        # Сохраняем в кэш
        if use_cache and redis_client is not None:
            try:
                await redis_client.set(
                    f"recommendations:{current_user.id}",
                    serialize_to_json(recommendations),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached recommendations for user {current_user.id}")
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

        return recommendations
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_recommendations",
                "user_id": current_user.id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise RecommendationException("Ошибка при получении рекомендаций")


@router.get("/stats", response_model=RecommendationStats)
async def get_recommendation_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> RecommendationStats:
    """
    Получение статистики рекомендаций для пользователя.

    Args:
        current_user: Текущий пользователь
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        RecommendationStats: Статистика рекомендаций
    """
    try:
        # Пытаемся получить статистику из кэша
        if redis_client is not None:
            try:
                cache_key = f"recommendation_stats:{current_user.id}"
                cached_stats = await redis_client.get(cache_key)
                if cached_stats:
                    try:
                        stats_data = deserialize_from_json(cached_stats)
                        log_info(f"Successfully retrieved recommendation stats from cache for user {current_user.id}")
                        return RecommendationStats(**stats_data)
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_stats",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_recommendation_stats",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Если кэш недоступен или пуст, получаем из БД
        recommendation_service = RecommendationService(db)
        stats = await recommendation_service.get_recommendation_stats(current_user.id)

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(stats),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached recommendation stats for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_recommendation_stats",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return stats
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_recommendation_stats",
                "user_id": current_user.id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise RecommendationException("Ошибка при получении статистики рекомендаций")


@router.get("/similar-users", response_model=List[Dict[str, Any]])
async def get_similar_users(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество похожих пользователей"),
) -> List[Dict[str, Any]]:
    """Получение списка похожих пользователей"""
    try:
        # Пытаемся получить список из кэша
        if redis_client is not None:
            try:
                cached_users = await redis_client.get(f"similar_users:{current_user.id}")
                if cached_users:
                    try:
                        users = deserialize_from_json(cached_users)
                        log_info(f"Successfully retrieved similar users from cache for user {current_user.id}")
                        return users
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_similar_users",
                                "key": f"similar_users:{current_user.id}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_similar_users",
                        "key": f"similar_users:{current_user.id}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Если кэш недоступен или пуст, получаем из БД
        recommendation_service = RecommendationService(db)
        users = await recommendation_service._get_similar_users(current_user.id, limit=limit)

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    f"similar_users:{current_user.id}", serialize_to_json(users), expire=3600  # 1 час
                )
                log_info(f"Successfully cached similar users for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_similar_users",
                        "key": f"similar_users:{current_user.id}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return users
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_similar_users",
                "user_id": current_user.id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise RecommendationException("Ошибка при получении списка похожих пользователей")


@router.get("/author/{author_id}", response_model=List[BookRecommendation])
async def get_author_recommendations(
    author_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(2.5, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_ratings_count: int = Query(3, ge=1, le=100, description="Минимальное количество оценок"),
    use_cache: bool = Query(True, description="Использовать кэширование"),
) -> List[BookRecommendation]:
    """
    Получение рекомендаций книг по автору.

    Args:
        author_id: ID автора
        db: Сессия базы данных
        redis_client: Клиент Redis
        current_user: Текущий пользователь
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг книг
        min_ratings_count: Минимальное количество оценок
        use_cache: Использовать кэширование

    Returns:
        List[BookRecommendation]: Список рекомендованных книг
    """
    try:
        # Пытаемся получить рекомендации из кэша
        if use_cache and redis_client is not None:
            try:
                cached_recommendations = await redis_client.get(f"author_recommendations:{author_id}:{current_user.id}")
                if cached_recommendations:
                    try:
                        recommendations = deserialize_from_json(cached_recommendations)
                        log_info(
                            f"Successfully retrieved {len(recommendations)} author recommendations from cache for user {current_user.id}"
                        )
                        return recommendations
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_author_recommendations",
                                "key": f"author_recommendations:{author_id}:{current_user.id}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_author_recommendations",
                        "key": f"author_recommendations:{author_id}:{current_user.id}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем рекомендации из базы данных
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_author_recommendations(
            user_id=current_user.id,
            author_id=author_id,
            limit=limit,
            min_rating=min_rating,
            min_ratings_count=min_ratings_count,
            cache=use_cache,
        )

        # Сохраняем в кэш
        if use_cache and redis_client is not None:
            try:
                await redis_client.set(
                    f"author_recommendations:{author_id}:{current_user.id}",
                    serialize_to_json(recommendations),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached author recommendations for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_author_recommendations",
                        "key": f"author_recommendations:{author_id}:{current_user.id}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return recommendations
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_author_recommendations",
                "user_id": current_user.id,
                "author_id": author_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise RecommendationException("Ошибка при получении рекомендаций по автору")


@router.get("/category/{category_id}", response_model=List[BookRecommendation])
async def get_category_recommendations(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(2.5, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_ratings_count: int = Query(3, ge=1, le=100, description="Минимальное количество оценок"),
    use_cache: bool = Query(True, description="Использовать кэширование"),
) -> List[BookRecommendation]:
    """
    Получение рекомендаций книг по категории.

    Args:
        category_id: ID категории
        db: Сессия базы данных
        redis_client: Клиент Redis
        current_user: Текущий пользователь
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг книг
        min_ratings_count: Минимальное количество оценок
        use_cache: Использовать кэширование

    Returns:
        List[BookRecommendation]: Список рекомендованных книг
    """
    try:
        # Пытаемся получить рекомендации из кэша
        if use_cache and redis_client is not None:
            try:
                cached_recommendations = await redis_client.get(
                    f"category_recommendations:{category_id}:{current_user.id}"
                )
                if cached_recommendations:
                    try:
                        recommendations = deserialize_from_json(cached_recommendations)
                        log_info(
                            f"Successfully retrieved {len(recommendations)} category recommendations from cache for user {current_user.id}"
                        )
                        return recommendations
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_category_recommendations",
                                "key": f"category_recommendations:{category_id}:{current_user.id}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_category_recommendations",
                        "key": f"category_recommendations:{category_id}:{current_user.id}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем рекомендации из базы данных
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_category_recommendations(
            user_id=current_user.id,
            category_id=category_id,
            limit=limit,
            min_rating=min_rating,
            min_ratings_count=min_ratings_count,
            cache=use_cache,
        )

        # Сохраняем в кэш
        if use_cache and redis_client is not None:
            try:
                await redis_client.set(
                    f"category_recommendations:{category_id}:{current_user.id}",
                    serialize_to_json(recommendations),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached category recommendations for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_category_recommendations",
                        "key": f"category_recommendations:{category_id}:{current_user.id}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return recommendations
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_category_recommendations",
                "user_id": current_user.id,
                "category_id": category_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise RecommendationException("Ошибка при получении рекомендаций по категории")


@router.get("/tag/{tag_id}", response_model=List[BookRecommendation])
async def get_tag_recommendations(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(2.5, ge=1.0, le=5.0, description="Минимальный рейтинг книг"),
    min_ratings_count: int = Query(3, ge=1, le=100, description="Минимальное количество оценок"),
    use_cache: bool = Query(True, description="Использовать кэширование"),
) -> List[BookRecommendation]:
    """
    Получение рекомендаций книг по тегу.

    Args:
        tag_id: ID тега
        db: Сессия базы данных
        redis_client: Клиент Redis
        current_user: Текущий пользователь
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг книг
        min_ratings_count: Минимальное количество оценок
        use_cache: Использовать кэширование

    Returns:
        List[BookRecommendation]: Список рекомендованных книг
    """
    try:
        # Пытаемся получить рекомендации из кэша
        if use_cache and redis_client is not None:
            try:
                cached_recommendations = await redis_client.get(f"tag_recommendations:{tag_id}:{current_user.id}")
                if cached_recommendations:
                    try:
                        recommendations = deserialize_from_json(cached_recommendations)
                        log_info(
                            f"Successfully retrieved {len(recommendations)} tag recommendations from cache for user {current_user.id}"
                        )
                        return recommendations
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_tag_recommendations",
                                "key": f"tag_recommendations:{tag_id}:{current_user.id}",
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_tag_recommendations",
                        "key": f"tag_recommendations:{tag_id}:{current_user.id}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем рекомендации из базы данных
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_tag_recommendations(
            user_id=current_user.id,
            tag_id=tag_id,
            limit=limit,
            min_rating=min_rating,
            min_ratings_count=min_ratings_count,
            cache=use_cache,
        )

        # Сохраняем в кэш
        if use_cache and redis_client is not None:
            try:
                await redis_client.set(
                    f"tag_recommendations:{tag_id}:{current_user.id}",
                    serialize_to_json(recommendations),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached tag recommendations for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_tag_recommendations",
                        "key": f"tag_recommendations:{tag_id}:{current_user.id}",
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return recommendations
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_tag_recommendations",
                "user_id": current_user.id,
                "tag_id": tag_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise RecommendationException("Ошибка при получении рекомендаций по тегу")


@router.get("/popular", response_model=List[BookRecommendation])
async def get_popular_recommendations(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(4.0, ge=0.0, le=5.0, description="Минимальный рейтинг"),
    min_ratings_count: int = Query(10, ge=1, description="Минимальное количество оценок"),
    use_cache: bool = Query(True, description="Использовать кэширование"),
) -> List[BookRecommendation]:
    """
    Получение популярных книг.

    Args:
        db: Сессия базы данных
        redis_client: Клиент Redis
        current_user: Текущий пользователь
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг
        min_ratings_count: Минимальное количество оценок
        use_cache: Использовать кэширование

    Returns:
        List[BookRecommendation]: Список рекомендуемых книг

    Raises:
        HTTPException: Если произошла ошибка при получении рекомендаций
    """
    try:
        # Пытаемся получить из кэша
        if use_cache and redis_client is not None:
            try:
                cache_key = f"popular_recommendations:{limit}:{min_rating}:{min_ratings_count}"
                cached_recommendations = await redis_client.get(cache_key)
                if cached_recommendations:
                    try:
                        recommendations_data = deserialize_from_json(cached_recommendations)
                        log_info(
                            f"Successfully retrieved {len(recommendations_data)} popular recommendations from cache"
                        )
                        return [BookRecommendation(**rec) for rec in recommendations_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_popular_recommendations",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_popular_recommendations",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем рекомендации из БД
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_popular_recommendations(
            limit=limit,
            min_rating=min_rating,
            min_ratings_count=min_ratings_count,
        )

        # Преобразуем в Pydantic модели
        recommendation_responses = [BookRecommendation.model_validate(rec) for rec in recommendations]

        # Сохраняем в кэш
        if use_cache and redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(recommendation_responses),
                    expire=3600,  # 1 час
                )
                log_info("Successfully cached popular recommendations")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_popular_recommendations",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return recommendation_responses
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_popular_recommendations",
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении популярных рекомендаций"
        )


@router.get("/collaborative", response_model=List[BookRecommendation])
async def get_collaborative_recommendations(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(4.0, ge=0.0, le=5.0, description="Минимальный рейтинг"),
    min_ratings_count: int = Query(10, ge=1, description="Минимальное количество оценок"),
    use_cache: bool = Query(True, description="Использовать кэширование"),
) -> List[BookRecommendation]:
    """
    Получение коллаборативных рекомендаций.

    Args:
        db: Сессия базы данных
        redis_client: Клиент Redis
        current_user: Текущий пользователь
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг
        min_ratings_count: Минимальное количество оценок
        use_cache: Использовать кэширование

    Returns:
        List[BookRecommendation]: Список рекомендуемых книг

    Raises:
        HTTPException: Если произошла ошибка при получении рекомендаций
    """
    try:
        # Пытаемся получить из кэша
        if use_cache and redis_client is not None:
            try:
                cache_key = f"collaborative_recommendations:{current_user.id}:{limit}:{min_rating}:{min_ratings_count}"
                cached_recommendations = await redis_client.get(cache_key)
                if cached_recommendations:
                    try:
                        recommendations_data = deserialize_from_json(cached_recommendations)
                        log_info(
                            f"Successfully retrieved {len(recommendations_data)} collaborative recommendations from cache for user {current_user.id}"
                        )
                        return [BookRecommendation(**rec) for rec in recommendations_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_collaborative_recommendations",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_collaborative_recommendations",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем рекомендации из БД
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_collaborative_recommendations(
            user_id=current_user.id,
            limit=limit,
            min_rating=min_rating,
            min_ratings_count=min_ratings_count,
        )

        # Преобразуем в Pydantic модели
        recommendation_responses = [BookRecommendation.model_validate(rec) for rec in recommendations]

        # Сохраняем в кэш
        if use_cache and redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(recommendation_responses),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached collaborative recommendations for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_collaborative_recommendations",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return recommendation_responses
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_collaborative_recommendations",
                "user_id": current_user.id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении коллаборативных рекомендаций",
        )


@router.get("/content", response_model=List[BookRecommendation])
async def get_content_based_recommendations(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(4.0, ge=0.0, le=5.0, description="Минимальный рейтинг"),
    min_ratings_count: int = Query(10, ge=1, description="Минимальное количество оценок"),
    use_cache: bool = Query(True, description="Использовать кэширование"),
) -> List[BookRecommendation]:
    """
    Получение контентных рекомендаций.

    Args:
        db: Сессия базы данных
        redis_client: Клиент Redis
        current_user: Текущий пользователь
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг
        min_ratings_count: Минимальное количество оценок
        use_cache: Использовать кэширование

    Returns:
        List[BookRecommendation]: Список рекомендуемых книг

    Raises:
        HTTPException: Если произошла ошибка при получении рекомендаций
    """
    try:
        # Пытаемся получить из кэша
        if use_cache and redis_client is not None:
            try:
                cache_key = f"content_recommendations:{current_user.id}:{limit}:{min_rating}:{min_ratings_count}"
                cached_recommendations = await redis_client.get(cache_key)
                if cached_recommendations:
                    try:
                        recommendations_data = deserialize_from_json(cached_recommendations)
                        log_info(
                            f"Successfully retrieved {len(recommendations_data)} content-based recommendations from cache for user {current_user.id}"
                        )
                        return [BookRecommendation(**rec) for rec in recommendations_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_content_recommendations",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_content_recommendations",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем рекомендации из БД
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_content_based_recommendations(
            user_id=current_user.id,
            limit=limit,
            min_rating=min_rating,
            min_ratings_count=min_ratings_count,
        )

        # Преобразуем в Pydantic модели
        recommendation_responses = [BookRecommendation.model_validate(rec) for rec in recommendations]

        # Сохраняем в кэш
        if use_cache and redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(recommendation_responses),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached content-based recommendations for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_content_recommendations",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return recommendation_responses
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_content_recommendations",
                "user_id": current_user.id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении контентных рекомендаций"
        )


@router.get("/hybrid", response_model=List[BookRecommendation])
async def get_hybrid_recommendations(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество рекомендаций"),
    min_rating: float = Query(4.0, ge=0.0, le=5.0, description="Минимальный рейтинг"),
    min_ratings_count: int = Query(10, ge=1, description="Минимальное количество оценок"),
    use_cache: bool = Query(True, description="Использовать кэширование"),
) -> List[BookRecommendation]:
    """
    Получение гибридных рекомендаций.

    Args:
        db: Сессия базы данных
        redis_client: Клиент Redis
        current_user: Текущий пользователь
        limit: Максимальное количество рекомендаций
        min_rating: Минимальный рейтинг
        min_ratings_count: Минимальное количество оценок
        use_cache: Использовать кэширование

    Returns:
        List[BookRecommendation]: Список рекомендуемых книг

    Raises:
        HTTPException: Если произошла ошибка при получении рекомендаций
    """
    try:
        # Пытаемся получить из кэша
        if use_cache and redis_client is not None:
            try:
                cache_key = f"hybrid_recommendations:{current_user.id}:{limit}:{min_rating}:{min_ratings_count}"
                cached_recommendations = await redis_client.get(cache_key)
                if cached_recommendations:
                    try:
                        recommendations_data = deserialize_from_json(cached_recommendations)
                        log_info(
                            f"Successfully retrieved {len(recommendations_data)} hybrid recommendations from cache for user {current_user.id}"
                        )
                        return [BookRecommendation(**rec) for rec in recommendations_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_hybrid_recommendations",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_hybrid_recommendations",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем рекомендации из БД
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_hybrid_recommendations(
            user_id=current_user.id,
            limit=limit,
            min_rating=min_rating,
            min_ratings_count=min_ratings_count,
        )

        # Преобразуем в Pydantic модели
        recommendation_responses = [BookRecommendation.model_validate(rec) for rec in recommendations]

        # Сохраняем в кэш
        if use_cache and redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(recommendation_responses),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached hybrid recommendations for user {current_user.id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_hybrid_recommendations",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return recommendation_responses
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_hybrid_recommendations",
                "user_id": current_user.id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении гибридных рекомендаций"
        )
