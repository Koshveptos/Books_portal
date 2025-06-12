import json
from typing import Any, List, Optional

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotEnoughDataForRecommendationException, RecommendationException
from app.core.logger_config import logger


class RecommendationService:
    """Гибридная рекомендательная система, сочетающая коллаборативную и контентную фильтрацию."""

    def __init__(self, db: AsyncSession, redis_client: Optional[Redis] = None):
        self.db = db
        self.redis_client = redis_client
        self.content_weight = 0.4  # Вес контентной фильтрации
        self.collaborative_weight = 0.6  # Вес коллаборативной фильтрации
        self.cache_ttl = 600  # 10 минут в секундах

    async def get_user_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        min_rating: float = 3.0,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        min_ratings_count: int = 5,
        recommendation_type: RecommendationType = RecommendationType.HYBRID,
        cache: bool = True,
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации для пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_year: Минимальный год издания
            max_year: Максимальный год издания
            min_ratings_count: Минимальное количество оценок
            recommendation_type: Тип рекомендаций
            cache: Использовать кэширование

        Returns:
            Список рекомендованных книг
        """
        try:
            # Проверяем кэш
            if cache and self.redis_client:
                try:
                    cache_key = self._get_cache_key(
                        user_id,
                        "recommendations",
                        type=recommendation_type.value,
                        limit=limit,
                        min_rating=min_rating,
                        min_year=min_year,
                        max_year=max_year,
                        min_ratings_count=min_ratings_count,
                    )
                    cached_recommendations = await self._get_cached_result(cache_key)
                    if cached_recommendations:
                        logger.info(f"Using cached recommendations for user {user_id}")
                        return [BookRecommendation(**item) for item in cached_recommendations]
                except Exception as e:
                    logger.error(f"Error getting cached recommendations: {str(e)}")
                    # Продолжаем выполнение без кэша

            # Получаем предпочтения пользователя
            user_preferences = await self._get_user_preferences(user_id)

            # Проверяем наличие данных для рекомендаций
            if not user_preferences.get("rated_books"):
                logger.warning(f"Недостаточно данных для рекомендаций пользователя {user_id}")
                raise NotEnoughDataForRecommendationException(
                    "Недостаточно данных для формирования рекомендаций. Пожалуйста, оцените несколько книг."
                )

            # Получаем рекомендации в соответствии с выбранной стратегией
            recommendations = []
            if recommendation_type == RecommendationType.HYBRID:
                recommendations = await self._get_hybrid_recommendations(
                    user_id=user_id, limit=limit, min_rating=min_rating, min_ratings_count=min_ratings_count
                )
            elif recommendation_type == RecommendationType.COLLABORATIVE:
                recommendations = await self._get_collaborative_recommendations(
                    user_preferences=user_preferences,
                    limit=limit,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year,
                    min_ratings_count=min_ratings_count,
                    user_id=user_id,
                )
            elif recommendation_type == RecommendationType.CONTENT:
                recommendations = await self._get_content_recommendations(
                    user_preferences=user_preferences,
                    limit=limit,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year,
                    min_ratings_count=min_ratings_count,
                    user_id=user_id,
                )
            elif recommendation_type == RecommendationType.POPULARITY:
                recommendations = await self._get_popularity_recommendations(
                    limit=limit,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year,
                    min_ratings_count=min_ratings_count,
                    exclude_book_ids=set(user_preferences.get("rated_books", [])),
                )
            elif recommendation_type == RecommendationType.AUTHOR:
                recommendations = await self._get_author_recommendations(
                    user_preferences=user_preferences,
                    limit=limit,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year,
                    min_ratings_count=min_ratings_count,
                    user_id=user_id,
                )
            elif recommendation_type == RecommendationType.CATEGORY:
                recommendations = await self._get_category_recommendations(
                    user_preferences=user_preferences,
                    limit=limit,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year,
                    min_ratings_count=min_ratings_count,
                    user_id=user_id,
                )
            elif recommendation_type == RecommendationType.TAG:
                recommendations = await self._get_tag_recommendations(
                    user_preferences=user_preferences,
                    limit=limit,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year,
                    min_ratings_count=min_ratings_count,
                    user_id=user_id,
                )

            # Кэшируем результаты
            if cache and self.redis_client and recommendations:
                try:
                    cache_key = self._get_cache_key(
                        user_id,
                        "recommendations",
                        type=recommendation_type.value,
                        limit=limit,
                        min_rating=min_rating,
                        min_year=min_year,
                        max_year=max_year,
                        min_ratings_count=min_ratings_count,
                    )
                    await self._cache_result(cache_key, [r.dict() for r in recommendations])
                except Exception as e:
                    logger.error(f"Error caching recommendations: {str(e)}")

            return recommendations

        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            raise RecommendationException("Ошибка при получении рекомендаций")

    def _get_cache_key(self, user_id: int, prefix: str, **kwargs) -> str:
        """Генерация ключа кэша"""
        params = [f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None]
        return f"{prefix}:{user_id}:{':'.join(params)}"

    async def _cache_result(self, key: str, data: Any, expire_seconds: int = 3600) -> None:
        """
        Кэширует результат в Redis.

        Args:
            key: Ключ для кэширования
            data: Данные для кэширования
            expire_seconds: Время жизни записи в секундах
        """
        if not self.redis_client:
            logger.debug("Redis client not available, skipping cache")
            return

        try:
            # Преобразуем данные в JSON-совместимый формат
            json_data = jsonable_encoder(data)

            # Ограничиваем размер кэшируемых данных
            if isinstance(json_data, list) and len(json_data) > 10:
                logger.warning(f"Truncating cache data from {len(json_data)} to 10 items")
                json_data = json_data[:10]

            # Сериализуем в JSON
            cached_value = json.dumps(json_data)

            # Проверяем размер данных перед кэшированием
            if len(cached_value) > 1024 * 1024:  # 1MB limit
                logger.warning(f"Cache data too large ({len(cached_value)} bytes), skipping cache")
                return

            # Сохраняем в Redis
            await self.redis_client.setex(key, expire_seconds, cached_value)
            logger.debug(f"Cached result with key: {key}, expires in {expire_seconds}s")
        except json.JSONDecodeError as e:
            logger.error(
                "JSON serialization error while caching",
                extra={"error": str(e), "error_type": type(e).__name__, "key": key},
            )
        except Exception as e:
            logger.error("Error caching result", extra={"error": str(e), "error_type": type(e).__name__, "key": key})

    async def _get_cached_result(self, key: str) -> Optional[Any]:
        """
        Получает результат из кэша.

        Args:
            key: Ключ кэша

        Returns:
            Десериализованные данные или None, если кэш не найден
        """
        if not self.redis_client:
            return None

        try:
            cached = await self.redis_client.get(key)
            if cached:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError as e:
                    logger.error(
                        "JSON deserialization error for cached data",
                        extra={"error": str(e), "error_type": type(e).__name__, "key": key},
                    )
                    return None
            return None
        except Exception as e:
            logger.error(
                "Error retrieving cached result", extra={"error": str(e), "error_type": type(e).__name__, "key": key}
            )
            return None

    async def get_recommendation_stats(self, user_id: int) -> RecommendationStats:
        """
        Получение статистики рекомендаций для пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            RecommendationStats: Статистика рекомендаций
        """
        try:
            # Пробуем получить статистику из кэша
            if self.redis_client:
                try:
                    cache_key = f"recommendation_stats:{user_id}"
                    cached_stats = await self.redis_client.get(cache_key)

                    if cached_stats:
                        try:
                            stats_dict = json.loads(cached_stats)
                            logger.info(
                                f"Successfully retrieved recommendation stats from cache for user {user_id}",
                                extra={"cache_key": cache_key},
                            )
                            return RecommendationStats(**stats_dict)
                        except json.JSONDecodeError as e:
                            logger.error(
                                "Error decoding cached recommendation stats",
                                extra={
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                    "user_id": user_id,
                                    "cache_key": cache_key,
                                },
                            )
                except Exception as e:
                    logger.error(
                        "Error getting recommendation stats from cache",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "user_id": user_id,
                        },
                    )

            # Если кэш недоступен или пуст, получаем статистику из БД
            stats = await self._get_recommendation_stats_from_db(user_id)

            # Кэшируем статистику
            if self.redis_client:
                try:
                    cache_key = f"recommendation_stats:{user_id}"
                    await self.redis_client.set(cache_key, json.dumps(stats.dict()), ex=3600)  # Кэшируем на 1 час
                    logger.info(
                        f"Successfully cached recommendation stats for user {user_id}",
                        extra={"cache_key": cache_key},
                    )
                except Exception as e:
                    logger.error(
                        "Error caching recommendation stats",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "user_id": user_id,
                        },
                    )

            return stats
        except Exception as e:
            logger.error(
                "Error getting recommendation stats",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": user_id,
                },
            )
            raise RecommendationException("Ошибка при получении статистики рекомендаций")

    async def _get_recommendation_stats_from_db(self, user_id: int) -> RecommendationStats:
        """
        Получение статистики рекомендаций из базы данных.

        Args:
            user_id: ID пользователя

        Returns:
            RecommendationStats: Статистика рекомендаций
        """
        try:
            # Получаем количество оцененных книг
            rated_books_query = """
                SELECT COUNT(*) as count
                FROM ratings
                WHERE user_id = :user_id
            """
            rated_books_result = await self.db.execute(text(rated_books_query), {"user_id": user_id})
            rated_books_count = rated_books_result.scalar() or 0

            # Получаем количество лайков
            likes_query = """
                SELECT COUNT(*) as count
                FROM likes
                WHERE user_id = :user_id
            """
            likes_result = await self.db.execute(text(likes_query), {"user_id": user_id})
            likes_count = likes_result.scalar() or 0

            # Получаем количество избранных книг
            favorites_query = """
                SELECT COUNT(*) as count
                FROM favorites
                WHERE user_id = :user_id
            """
            favorites_result = await self.db.execute(text(favorites_query), {"user_id": user_id})
            favorites_count = favorites_result.scalar() or 0

            # Получаем количество любимых авторов
            authors_query = """
                SELECT COUNT(DISTINCT a.id) as count
                FROM authors a
                JOIN books b ON b.author_id = a.id
                JOIN ratings r ON r.book_id = b.id
                WHERE r.user_id = :user_id AND r.rating >= 4
            """
            authors_result = await self.db.execute(text(authors_query), {"user_id": user_id})
            authors_count = authors_result.scalar() or 0

            # Получаем количество любимых категорий
            categories_query = """
                SELECT COUNT(DISTINCT c.id) as count
                FROM categories c
                JOIN book_categories bc ON bc.category_id = c.id
                JOIN books b ON b.id = bc.book_id
                JOIN ratings r ON r.book_id = b.id
                WHERE r.user_id = :user_id AND r.rating >= 4
            """
            categories_result = await self.db.execute(text(categories_query), {"user_id": user_id})
            categories_count = categories_result.scalar() or 0

            # Получаем количество любимых тегов
            tags_query = """
                SELECT COUNT(DISTINCT t.id) as count
                FROM tags t
                JOIN book_tags bt ON bt.tag_id = t.id
                JOIN books b ON b.id = bt.book_id
                JOIN ratings r ON r.book_id = b.id
                WHERE r.user_id = :user_id AND r.rating >= 4
            """
            tags_result = await self.db.execute(text(tags_query), {"user_id": user_id})
            tags_count = tags_result.scalar() or 0

            # Формируем статистику
            stats = RecommendationStats(
                rated_books_count=rated_books_count,
                likes_count=likes_count,
                favorites_count=favorites_count,
                authors_count=authors_count,
                categories_count=categories_count,
                tags_count=tags_count,
                has_enough_data=rated_books_count >= 5,  # Минимум 5 оцененных книг для рекомендаций
            )

            logger.info(
                f"Successfully retrieved recommendation stats from DB for user {user_id}",
                extra={
                    "rated_books_count": rated_books_count,
                    "likes_count": likes_count,
                    "favorites_count": favorites_count,
                    "authors_count": authors_count,
                    "categories_count": categories_count,
                    "tags_count": tags_count,
                },
            )

            return stats
        except Exception as e:
            logger.error(
                "Error getting recommendation stats from DB",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": user_id,
                },
            )
            raise RecommendationException("Ошибка при получении статистики рекомендаций из базы данных")

    async def get_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        min_rating: float = 3.5,
        min_ratings_count: int = 5,
        recommendation_type: str = "hybrid",
    ) -> List[BookRecommendation]:
        """
        Получение рекомендаций для пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_ratings_count: Минимальное количество оценок для книги
            recommendation_type: Тип рекомендаций (hybrid, collaborative, content, popularity)

        Returns:
            List[BookRecommendation]: Список рекомендаций
        """
        try:
            # Пробуем получить рекомендации из кэша
            if self.redis_client:
                try:
                    cache_key = (
                        f"recommendations:{user_id}:{recommendation_type}:{limit}:{min_rating}:{min_ratings_count}"
                    )
                    cached_recommendations = await self.redis_client.get(cache_key)

                    if cached_recommendations:
                        try:
                            recommendations_dict = json.loads(cached_recommendations)
                            logger.info(
                                f"Successfully retrieved recommendations from cache for user {user_id}",
                                extra={
                                    "cache_key": cache_key,
                                    "recommendation_type": recommendation_type,
                                    "limit": limit,
                                },
                            )
                            return [BookRecommendation(**rec) for rec in recommendations_dict]
                        except json.JSONDecodeError as e:
                            logger.error(
                                "Error decoding cached recommendations",
                                extra={
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                    "user_id": user_id,
                                    "cache_key": cache_key,
                                },
                            )
                except Exception as e:
                    logger.error(
                        "Error getting recommendations from cache",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "user_id": user_id,
                        },
                    )

            # Если кэш недоступен или пуст, получаем рекомендации из БД
            recommendations = await self._get_recommendations_from_db(
                user_id=user_id,
                limit=limit,
                min_rating=min_rating,
                min_ratings_count=min_ratings_count,
                recommendation_type=recommendation_type,
            )

            # Кэшируем рекомендации
            if self.redis_client:
                try:
                    cache_key = (
                        f"recommendations:{user_id}:{recommendation_type}:{limit}:{min_rating}:{min_ratings_count}"
                    )
                    await self.redis_client.set(
                        cache_key, json.dumps([rec.dict() for rec in recommendations]), ex=3600  # Кэшируем на 1 час
                    )
                    logger.info(
                        f"Successfully cached recommendations for user {user_id}",
                        extra={
                            "cache_key": cache_key,
                            "recommendation_type": recommendation_type,
                            "limit": limit,
                        },
                    )
                except Exception as e:
                    logger.error(
                        "Error caching recommendations",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "user_id": user_id,
                        },
                    )

            return recommendations
        except Exception as e:
            logger.error(
                "Error getting recommendations",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": user_id,
                    "recommendation_type": recommendation_type,
                },
            )
            raise RecommendationException("Ошибка при получении рекомендаций")

    async def _get_recommendations_from_db(
        self,
        user_id: int,
        limit: int = 10,
        min_rating: float = 3.5,
        min_ratings_count: int = 5,
        recommendation_type: str = "hybrid",
    ) -> List[BookRecommendation]:
        """
        Получение рекомендаций из базы данных.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_ratings_count: Минимальное количество оценок для книги
            recommendation_type: Тип рекомендаций (hybrid, collaborative, content, popularity)

        Returns:
            List[BookRecommendation]: Список рекомендаций
        """
        try:
            # Выбираем стратегию рекомендаций
            if recommendation_type == "hybrid":
                recommendations = await self._get_hybrid_recommendations(
                    user_id=user_id, limit=limit, min_rating=min_rating, min_ratings_count=min_ratings_count
                )
            elif recommendation_type == "collaborative":
                recommendations = await self._get_collaborative_recommendations(
                    user_id=user_id, limit=limit, min_rating=min_rating, min_ratings_count=min_ratings_count
                )
            elif recommendation_type == "content":
                recommendations = await self._get_content_based_recommendations(
                    user_id=user_id, limit=limit, min_rating=min_rating, min_ratings_count=min_ratings_count
                )
            elif recommendation_type == "popularity":
                recommendations = await self._get_popular_recommendations(
                    user_id=user_id, limit=limit, min_rating=min_rating, min_ratings_count=min_ratings_count
                )
            else:
                logger.error(
                    "Invalid recommendation type",
                    extra={
                        "recommendation_type": recommendation_type,
                        "user_id": user_id,
                    },
                )
                raise RecommendationException(f"Неизвестный тип рекомендаций: {recommendation_type}")

            logger.info(
                f"Successfully retrieved recommendations from DB for user {user_id}",
                extra={
                    "recommendation_type": recommendation_type,
                    "limit": limit,
                    "recommendations_count": len(recommendations),
                },
            )

            return recommendations
        except Exception as e:
            logger.error(
                "Error getting recommendations from DB",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": user_id,
                    "recommendation_type": recommendation_type,
                },
            )
            raise RecommendationException("Ошибка при получении рекомендаций из базы данных")

    async def _get_hybrid_recommendations(
        self, user_id: int, limit: int = 10, min_rating: float = 3.5, min_ratings_count: int = 5
    ) -> List[BookRecommendation]:
        """
        Получение гибридных рекомендаций (комбинация коллаборативной фильтрации и контентной фильтрации).

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_ratings_count: Минимальное количество оценок для книги

        Returns:
            List[BookRecommendation]: Список рекомендаций
        """
        try:
            # Получаем рекомендации на основе коллаборативной фильтрации
            collaborative_recommendations = await self._get_collaborative_recommendations(
                user_id=user_id,
                limit=limit * 2,  # Получаем больше рекомендаций для лучшего смешивания
                min_rating=min_rating,
                min_ratings_count=min_ratings_count,
            )

            # Получаем рекомендации на основе контентной фильтрации
            content_recommendations = await self._get_content_based_recommendations(
                user_id=user_id,
                limit=limit * 2,  # Получаем больше рекомендаций для лучшего смешивания
                min_rating=min_rating,
                min_ratings_count=min_ratings_count,
            )

            # Объединяем и ранжируем рекомендации
            all_recommendations = {}

            # Добавляем рекомендации из коллаборативной фильтрации с весом 0.6
            for rec in collaborative_recommendations:
                if rec.book_id not in all_recommendations:
                    all_recommendations[rec.book_id] = rec
                    all_recommendations[rec.book_id].score *= 0.6
                else:
                    all_recommendations[rec.book_id].score = (
                        all_recommendations[rec.book_id].score * 0.6 + rec.score * 0.6
                    ) / 2

            # Добавляем рекомендации из контентной фильтрации с весом 0.4
            for rec in content_recommendations:
                if rec.book_id not in all_recommendations:
                    all_recommendations[rec.book_id] = rec
                    all_recommendations[rec.book_id].score *= 0.4
                else:
                    all_recommendations[rec.book_id].score = (
                        all_recommendations[rec.book_id].score * 0.4 + rec.score * 0.4
                    ) / 2

            # Сортируем по убыванию score и берем limit лучших
            recommendations = sorted(all_recommendations.values(), key=lambda x: x.score, reverse=True)[:limit]

            logger.info(
                f"Successfully generated hybrid recommendations for user {user_id}",
                extra={
                    "collaborative_count": len(collaborative_recommendations),
                    "content_count": len(content_recommendations),
                    "final_count": len(recommendations),
                    "limit": limit,
                },
            )

            return recommendations
        except Exception as e:
            logger.error(
                "Error generating hybrid recommendations",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": user_id,
                },
            )
            raise RecommendationException("Ошибка при генерации гибридных рекомендаций")
