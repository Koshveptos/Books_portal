import json
from typing import List, Optional

from core.dependencies import get_current_active_user, get_db, get_redis_client
from core.exceptions import (
    CacheException,
    DatabaseException,
    NotEnoughDataForRecommendationException,
    RecommendationException,
)
from core.logger_config import (
    log_cache_error,
    log_db_error,
    log_info,
    log_warning,
)
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from models.user import User
from redis import Redis
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType, SimilarUser
from services.recommendations import (
    RecommendationService,
    get_author_recommendations_from_db,
    get_category_recommendations_from_db,
    get_recommendation_stats_from_db,
    get_similar_users_from_db,
    get_tag_recommendations_from_db,
)
from sqlalchemy.ext.asyncio import AsyncSession

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
        log_db_error(error=e, operation="get_recommendations_from_db", table="recommendations")
        raise RecommendationException("Ошибка при получении рекомендаций из базы данных")


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
        if use_cache:
            try:
                cached_recommendations = await redis_client.get(f"recommendations:{current_user.id}")
                if cached_recommendations:
                    return json.loads(cached_recommendations)
            except Exception as e:
                log_cache_error(e, operation="get_recommendations", key=f"recommendations:{current_user.id}")

        # Получаем рекомендации из базы данных
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
            log_info(f"No recommendations found for user {current_user.id}")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"message": "Рекомендации не найдены. Попробуйте изменить параметры запроса."},
            )

        log_info(f"Found {len(recommendations)} recommendations for user {current_user.id}")

        # Сохраняем в кэш
        if use_cache:
            try:
                await redis_client.set(
                    f"recommendations:{current_user.id}", json.dumps(recommendations), expire=3600  # 1 час
                )
            except Exception as e:
                log_cache_error(e, operation="cache_recommendations", key=f"recommendations:{current_user.id}")

        return recommendations
    except NotEnoughDataForRecommendationException as e:
        log_warning(f"Not enough data for recommendations: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content={"message": str(e)},
        )
    except Exception as e:
        log_db_error(error=e, operation="get_recommendations", table="recommendations")
        raise RecommendationException("Ошибка при получении рекомендаций")


@router.get("/stats", response_model=RecommendationStats)
async def get_recommendation_stats(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить статистику для персональных рекомендаций.

    Возвращает информацию о предпочтениях пользователя, количестве оцененных книг,
    любимых авторах, категориях и тегах, а также готовности системы
    предоставлять различные типы рекомендаций для этого пользователя.
    """
    try:
        log_info(f"Getting recommendation stats for user {current_user.id}")

        # Пытаемся получить статистику из кэша
        cached_stats = await redis_client.get(f"recommendation_stats:{current_user.id}")
        if cached_stats:
            return json.loads(cached_stats)

        # Если в кэше нет, получаем статистику из базы данных
        recommendation_service = RecommendationService(db, redis_client)
        stats = await recommendation_service.get_recommendation_stats(user_id=current_user.id)

        log_info(f"Successfully retrieved recommendation stats for user {current_user.id}")

        # Сохраняем в кэш
        await redis_client.set(f"recommendation_stats:{current_user.id}", json.dumps(stats), expire=3600)  # 1 час

        return stats
    except CacheException as e:
        log_cache_error(e, operation="get_recommendation_stats", key=f"recommendation_stats:{current_user.id}")
        # Если кэш недоступен, получаем статистику из базы данных
        return await get_recommendation_stats_from_db(current_user.id, db)
    except Exception as e:
        log_db_error(e, operation="get_recommendation_stats", user_id=current_user.id)
        raise DatabaseException("Ошибка при получении статистики рекомендаций")


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

    Этот эндпоинт находит пользователей с похожими вкусами на основе
    оценок книг. Используется для коллаборативной фильтрации и
    помогает пользователям найти единомышленников.
    """
    try:
        log_info(
            f"Getting similar users for user {current_user.id} with "
            f"limit={limit}, min_common_ratings={min_common_ratings}"
        )

        # Пытаемся получить похожих пользователей из кэша
        cached_users = await redis_client.get(f"similar_users:{current_user.id}")
        if cached_users:
            return json.loads(cached_users)

        # Если в кэше нет, получаем похожих пользователей из базы данных
        recommendation_service = RecommendationService(db, redis_client)
        similar_users = await recommendation_service.get_similar_users(
            user_id=current_user.id, limit=limit, min_common_ratings=min_common_ratings
        )

        if not similar_users:
            log_info(f"No similar users found for user {current_user.id}")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"message": "Похожие пользователи не найдены. Возможно, у вас пока недостаточно оценок."},
            )

        log_info(f"Found {len(similar_users)} similar users for user {current_user.id}")

        # Сохраняем в кэш
        await redis_client.set(f"similar_users:{current_user.id}", json.dumps(similar_users), expire=3600)  # 1 час

        return similar_users
    except CacheException as e:
        log_cache_error(e, operation="get_similar_users", key=f"similar_users:{current_user.id}")
        # Если кэш недоступен, получаем похожих пользователей из базы данных
        return await get_similar_users_from_db(current_user.id, db)
    except Exception as e:
        log_db_error(e, operation="get_similar_users", user_id=current_user.id)
        raise DatabaseException("Ошибка при получении похожих пользователей")


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

    Этот эндпоинт анализирует оценки пользователя, определяет
    любимых авторов и рекомендует непрочитанные книги этих авторов.
    """
    try:
        log_info(
            f"Getting author recommendations for user {current_user.id} with "
            f"limit={limit}, min_rating={min_rating}, min_ratings_count={min_ratings_count}"
        )

        # Пытаемся получить рекомендации по автору из кэша
        cached_recommendations = await redis_client.get(f"author_recommendations:{current_user.id}")
        if cached_recommendations:
            return json.loads(cached_recommendations)

        # Если в кэше нет, получаем рекомендации из базы данных
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
            log_info(f"No author recommendations found for user {current_user.id}")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={
                    "message": "Рекомендации по авторам не найдены. Возможно, у вас нет любимых авторов или вы уже прочитали все их книги."
                },
            )

        log_info(f"Found {len(recommendations)} author recommendations for user {current_user.id}")

        # Сохраняем в кэш
        await redis_client.set(
            f"author_recommendations:{current_user.id}", json.dumps(recommendations), expire=3600  # 1 час
        )

        return recommendations
    except CacheException as e:
        log_cache_error(e, operation="get_author_recommendations", key=f"author_recommendations:{current_user.id}")
        # Если кэш недоступен, получаем рекомендации из базы данных
        return await get_author_recommendations_from_db(current_user.id, db)
    except Exception as e:
        log_db_error(e, operation="get_author_recommendations", user_id=current_user.id)
        raise DatabaseException("Ошибка при получении рекомендаций по автору")


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

    Этот эндпоинт анализирует оценки пользователя, определяет
    любимые категории и рекомендует непрочитанные книги из этих категорий.
    """
    try:
        log_info(
            f"Getting category recommendations for user {current_user.id} with "
            f"limit={limit}, min_rating={min_rating}, min_ratings_count={min_ratings_count}"
        )

        # Пытаемся получить рекомендации по категории из кэша
        cached_recommendations = await redis_client.get(f"category_recommendations:{current_user.id}")
        if cached_recommendations:
            return json.loads(cached_recommendations)

        # Если в кэше нет, получаем рекомендации из базы данных
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
            log_info(f"No category recommendations found for user {current_user.id}")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"message": "Рекомендации по категориям не найдены. Возможно, у вас нет любимых категорий."},
            )

        log_info(f"Found {len(recommendations)} category recommendations for user {current_user.id}")

        # Сохраняем в кэш
        await redis_client.set(
            f"category_recommendations:{current_user.id}", json.dumps(recommendations), expire=3600  # 1 час
        )

        return recommendations
    except CacheException as e:
        log_cache_error(e, operation="get_category_recommendations", key=f"category_recommendations:{current_user.id}")
        # Если кэш недоступен, получаем рекомендации из базы данных
        return await get_category_recommendations_from_db(current_user.id, db)
    except Exception as e:
        log_db_error(e, operation="get_category_recommendations", user_id=current_user.id)
        raise DatabaseException("Ошибка при получении рекомендаций по категории")


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

    Этот эндпоинт анализирует оценки пользователя, определяет
    любимые теги и рекомендует непрочитанные книги с этими тегами.
    """
    try:
        log_info(
            f"Getting tag recommendations for user {current_user.id} with "
            f"limit={limit}, min_rating={min_rating}, min_ratings_count={min_ratings_count}"
        )

        # Пытаемся получить рекомендации по тегу из кэша
        cached_recommendations = await redis_client.get(f"tag_recommendations:{current_user.id}")
        if cached_recommendations:
            return json.loads(cached_recommendations)

        # Если в кэше нет, получаем рекомендации из базы данных
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
            log_info(f"No tag recommendations found for user {current_user.id}")
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"message": "Рекомендации по тегам не найдены. Возможно, у вас нет любимых тегов."},
            )

        log_info(f"Found {len(recommendations)} tag recommendations for user {current_user.id}")

        # Сохраняем в кэш
        await redis_client.set(
            f"tag_recommendations:{current_user.id}", json.dumps(recommendations), expire=3600  # 1 час
        )

        return recommendations
    except CacheException as e:
        log_cache_error(e, operation="get_tag_recommendations", key=f"tag_recommendations:{current_user.id}")
        # Если кэш недоступен, получаем рекомендации из базы данных
        return await get_tag_recommendations_from_db(current_user.id, db)
    except Exception as e:
        log_db_error(e, operation="get_tag_recommendations", user_id=current_user.id)
        raise DatabaseException("Ошибка при получении рекомендаций по тегу")
