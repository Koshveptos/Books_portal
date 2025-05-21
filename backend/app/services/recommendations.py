import json
from typing import Any, Dict, List, Optional

from core.exceptions import NotEnoughDataForRecommendationException, RecommendationException
from core.logger_config import logger
from fastapi.encoders import jsonable_encoder
from redis import Redis
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
        Получает рекомендации книг для пользователя.
        """
        try:
            logger.info(f"Начинаем получение рекомендаций для пользователя {user_id}")

            # Ограничиваем максимальное количество рекомендаций
            if limit > 20:
                logger.warning(f"Limiting recommendations from {limit} to 20")
                limit = 20

            # Проверяем наличие кэшированных результатов, если необходимо кэширование
            cache_key = None
            if cache and self.redis_client:
                try:
                    cache_key = self.get_cache_key(
                        user_id,
                        "recommendations",
                        type=recommendation_type.value,
                        limit=limit,
                        min_rating=min_rating,
                        min_year=min_year,
                        max_year=max_year,
                        min_ratings_count=min_ratings_count,
                    )
                    cached_recommendations = self.get_cached_result(cache_key)
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
                    "Недостаточно данных для формирования рекомендаций. " "Пожалуйста, оцените несколько книг."
                )

            # Получаем рекомендации в соответствии с выбранной стратегией
            recommendations = []
            logger.info(f"Получаем рекомендации типа {recommendation_type.value}")

            try:
                if recommendation_type == RecommendationType.COLLABORATIVE:
                    recommendations = await self._get_collaborative_recommendations(
                        user_id=user_id,
                        limit=limit,
                        min_rating=min_rating,
                        min_year=min_year,
                        max_year=max_year,
                        min_ratings_count=min_ratings_count,
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
                elif recommendation_type == RecommendationType.POPULARITY:
                    recommendations = await self._get_popularity_recommendations(
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
                else:  # RecommendationType.HYBRID
                    logger.info("Получаем гибридные рекомендации")
                    # Для гибридных рекомендаций объединяем результаты различных стратегий
                    collaborative_recs = await self._get_collaborative_recommendations(
                        user_id=user_id,
                        limit=limit,
                        min_rating=min_rating,
                        min_year=min_year,
                        max_year=max_year,
                        min_ratings_count=min_ratings_count,
                    )
                    logger.info(f"Получено {len(collaborative_recs)} коллаборативных рекомендаций")

                    content_recs = await self._get_content_recommendations(
                        user_preferences=user_preferences,
                        limit=limit,
                        min_rating=min_rating,
                        min_year=min_year,
                        max_year=max_year,
                        min_ratings_count=min_ratings_count,
                        user_id=user_id,
                    )
                    logger.info(f"Получено {len(content_recs)} контентных рекомендаций")

                    popularity_recs = await self._get_popularity_recommendations(
                        limit=limit,
                        min_rating=min_rating,
                        min_year=min_year,
                        max_year=max_year,
                        min_ratings_count=min_ratings_count,
                        user_id=user_id,
                    )
                    logger.info(f"Получено {len(popularity_recs)} популярных рекомендаций")

                    # Объединяем все рекомендации с весами
                    hybrid_recs = {}

                    # Добавляем коллаборативные рекомендации с весом 2.0
                    for rec in collaborative_recs:
                        hybrid_recs[rec.id] = {"rec": rec, "score": rec.score * 2.0}

                    # Добавляем контентные рекомендации с весом 1.5
                    for rec in content_recs:
                        if rec.id in hybrid_recs:
                            hybrid_recs[rec.id]["score"] += rec.score * 1.5
                        else:
                            hybrid_recs[rec.id] = {"rec": rec, "score": rec.score * 1.5}

                    # Добавляем популярные рекомендации с весом 1.0
                    for rec in popularity_recs:
                        if rec.id in hybrid_recs:
                            hybrid_recs[rec.id]["score"] += rec.score * 1.0
                        else:
                            hybrid_recs[rec.id] = {"rec": rec, "score": rec.score * 1.0}

                    # Сортируем результаты по итоговому весу
                    sorted_recs = sorted(hybrid_recs.values(), key=lambda x: x["score"], reverse=True)
                    recommendations = [
                        BookRecommendation(
                            id=item["rec"].id,
                            title=item["rec"].title,
                            author=item["rec"].author,
                            category=item["rec"].category,
                            rating=item["rec"].rating,
                            score=item["score"],
                            reason=f"Комбинированная рекомендация (вес: {item['score']:.2f})",
                            recommendation_type=RecommendationType.HYBRID,
                        )
                        for item in sorted_recs[:limit]
                    ]
                    logger.info(f"Сформировано {len(recommendations)} гибридных рекомендаций")
            except Exception as e:
                logger.error(
                    f"Ошибка при получении рекомендаций типа {recommendation_type.value}: {str(e)}", exc_info=True
                )
                raise

            if not recommendations:
                logger.warning(f"Не найдено рекомендаций для пользователя {user_id}")
                raise NotEnoughDataForRecommendationException(
                    "Не удалось найти подходящие рекомендации. " "Попробуйте изменить параметры запроса."
                )

            # Кэшируем результаты
            if cache and cache_key and self.redis_client:
                try:
                    self.cache_result(cache_key, recommendations, expire_seconds=3600)
                    logger.info(f"Рекомендации закэшированы для пользователя {user_id}")
                except Exception as e:
                    logger.error(f"Error caching recommendations: {str(e)}")
                    # Продолжаем выполнение без кэширования

            logger.info(f"Успешно получены {len(recommendations)} рекомендаций для пользователя {user_id}")
            return recommendations

        except NotEnoughDataForRecommendationException:
            raise
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {str(e)}", exc_info=True)
            raise RecommendationException("Ошибка при получении рекомендаций")

    async def get_similar_users(
        self, user_id: int, limit: int = 10, min_common_ratings: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Получить список похожих пользователей.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество похожих пользователей
            min_common_ratings: Минимальное количество общих оценок

        Returns:
            List[Dict]: Список похожих пользователей с информацией о схожести
        """
        try:
            query = text(
                """
                WITH user_ratings AS (
                    SELECT book_id, rating
                    FROM ratings
                    WHERE user_id = :user_id
                ),
                similar_users AS (
                    SELECT
                        r.user_id,
                        COUNT(*) as common_ratings,
                        AVG(ABS(ur.rating - r.rating)) as rating_diff,
                        CORR(ur.rating, r.rating) as correlation
                    FROM ratings r
                    JOIN user_ratings ur ON r.book_id = ur.book_id
                    WHERE r.user_id != :user_id
                    GROUP BY r.user_id
                    HAVING COUNT(*) >= :min_common_ratings
                )
                SELECT
                    u.id,
                    u.email,
                    su.common_ratings,
                    su.rating_diff,
                    su.correlation
                FROM similar_users su
                JOIN users u ON u.id = su.user_id
                ORDER BY su.correlation DESC, su.rating_diff ASC
                LIMIT :limit
            """
            )

            result = await self.db.execute(
                query, {"user_id": user_id, "min_common_ratings": min_common_ratings, "limit": limit}
            )
            similar_users = result.fetchall()

            # Логируем статистику
            logger.info(
                f"Найдено {len(similar_users)} похожих пользователей для пользователя {user_id}, "
                f"минимальное количество общих оценок: {min_common_ratings}"
            )

            return [dict(user) for user in similar_users]

        except Exception as e:
            logger.error(f"Ошибка при поиске похожих пользователей: {str(e)}", exc_info=True)
            raise

    async def _get_recommendation_reason(self, book: Any, user_preferences: Dict[str, Any]) -> str:
        """
        Получить причину рекомендации книги.
        """
        try:
            logger.info(f"Формируем причину рекомендации для книги {book.id}")
            reasons = []

            # Проверяем совпадение с авторами
            if book.author:
                author_names = book.author.split(", ")
                for author_name in author_names:
                    if any(
                        author_name in pref.get("name", "") for pref in user_preferences.get("authors", {}).values()
                    ):
                        reasons.append(f"Вам понравились книги автора {author_name}")
                        break

            # Проверяем совпадение с категориями
            if book.category:
                category_names = book.category.split(", ")
                for category_name in category_names:
                    if any(
                        category_name in pref.get("name", "")
                        for pref in user_preferences.get("categories", {}).values()
                    ):
                        reasons.append(f"Вам нравятся книги в категории {category_name}")
                        break

            if not reasons:
                reasons.append("Похожие пользователи высоко оценили эту книгу")

            reason = " и ".join(reasons)
            logger.info(f"Сформирована причина рекомендации для книги {book.id}: {reason}")
            return reason

        except Exception as e:
            logger.error(f"Ошибка при формировании причины рекомендации для книги {book.id}: {str(e)}", exc_info=True)
            return "Рекомендуемая книга"

    async def _get_author_recommendations(
        self,
        user_preferences: Dict[str, Any],
        limit: int,
        min_rating: float,
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        user_id: int,
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе предпочитаемых авторов.
        """
        try:
            favorite_authors = list(user_preferences.get("authors", {}).keys())
            if not favorite_authors:
                return []

            query = text(
                """
                SELECT DISTINCT b.*
                FROM books b
                JOIN book_authors ba ON b.id = ba.book_id
                WHERE ba.author_id = ANY(:author_ids)
                AND b.id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                ORDER BY b.year DESC
                LIMIT :limit
            """
            )

            result = await self.db.execute(query, {"author_ids": favorite_authors, "user_id": user_id, "limit": limit})
            books = result.fetchall()

            return [BookRecommendation(**book) for book in books]

        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций по авторам: {str(e)}", exc_info=True)
            return []

    async def _get_category_recommendations(
        self,
        user_preferences: Dict[str, Any],
        limit: int,
        min_rating: float,
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        user_id: int,
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе предпочитаемых категорий.
        """
        try:
            favorite_categories = list(user_preferences.get("categories", {}).keys())
            if not favorite_categories:
                return []

            query = text(
                """
                SELECT DISTINCT b.*
                FROM books b
                JOIN book_categories bc ON b.id = bc.book_id
                WHERE bc.category_id = ANY(:category_ids)
                AND b.id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                ORDER BY b.year DESC
                LIMIT :limit
            """
            )

            result = await self.db.execute(
                query, {"category_ids": favorite_categories, "user_id": user_id, "limit": limit}
            )
            books = result.fetchall()

            return [BookRecommendation(**book) for book in books]

        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций по категориям: {str(e)}", exc_info=True)
            return []

    async def _get_tag_recommendations(
        self,
        user_preferences: Dict[str, Any],
        limit: int,
        min_rating: float,
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        user_id: int,
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе предпочитаемых тегов.
        """
        try:
            favorite_tags = list(user_preferences.get("tags", {}).keys())
            if not favorite_tags:
                return []

            query = text(
                """
                SELECT DISTINCT b.*
                FROM books b
                JOIN book_tags bt ON b.id = bt.book_id
                WHERE bt.tag_id = ANY(:tag_ids)
                AND b.id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                ORDER BY b.year DESC
                LIMIT :limit
            """
            )

            result = await self.db.execute(query, {"tag_ids": favorite_tags, "user_id": user_id, "limit": limit})
            books = result.fetchall()

            return [BookRecommendation(**book) for book in books]

        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций по тегам: {str(e)}", exc_info=True)
            return []

    async def _get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        Получить предпочтения пользователя на основе его оценок, лайков и избранного.
        """
        try:
            logger.info(f"Начинаем получение предпочтений для пользователя {user_id}")

            # Получаем список оцененных книг
            rated_books_query = text(
                """
                SELECT DISTINCT book_id
                FROM ratings
                WHERE user_id = :user_id
                """
            )
            rated_books_result = await self.db.execute(rated_books_query, {"user_id": user_id})
            rated_books = [row[0] for row in rated_books_result.fetchall()]
            logger.info(f"Получено {len(rated_books)} оцененных книг")

            # Получаем предпочтения по оценкам
            ratings_query = text(
                """
                SELECT
                    a.id as author_id,
                    a.name as author_name,
                    c.id as category_id,
                    c.name_categories as category_name,
                    t.id as tag_id,
                    t.name_tag as tag_name,
                    AVG(r.rating) as avg_rating,
                    COUNT(*) as interaction_count
                FROM ratings r
                JOIN books b ON r.book_id = b.id
                LEFT JOIN book_authors ba ON b.id = ba.book_id
                LEFT JOIN authors a ON ba.author_id = a.id
                LEFT JOIN books_categories bc ON b.id = bc.book_id
                LEFT JOIN categories c ON bc.category_id = c.id
                LEFT JOIN books_tags bt ON b.id = bt.book_id
                LEFT JOIN tags t ON bt.tag_id = t.id
                WHERE r.user_id = :user_id
                GROUP BY a.id, a.name, c.id, c.name_categories, t.id, t.name_tag
                HAVING AVG(r.rating) >= 3.0
            """
            )

            logger.info("Выполняем запрос для получения предпочтений по оценкам")
            ratings_result = await self.db.execute(ratings_query, {"user_id": user_id})
            ratings_data = ratings_result.fetchall()
            logger.info(f"Получено {len(ratings_data)} записей по оценкам")

            # Получаем предпочтения по лайкам
            likes_query = text(
                """
                SELECT
                    a.id as author_id,
                    a.name as author_name,
                    c.id as category_id,
                    c.name_categories as category_name,
                    t.id as tag_id,
                    t.name_tag as tag_name,
                    1 as interaction_count
                FROM likes l
                JOIN books b ON l.book_id = b.id
                LEFT JOIN book_authors ba ON b.id = ba.book_id
                LEFT JOIN authors a ON ba.author_id = a.id
                LEFT JOIN books_categories bc ON b.id = bc.book_id
                LEFT JOIN categories c ON bc.category_id = c.id
                LEFT JOIN books_tags bt ON b.id = bt.book_id
                LEFT JOIN tags t ON bt.tag_id = t.id
                WHERE l.user_id = :user_id
            """
            )

            logger.info("Выполняем запрос для получения предпочтений по лайкам")
            likes_result = await self.db.execute(likes_query, {"user_id": user_id})
            likes_data = likes_result.fetchall()
            logger.info(f"Получено {len(likes_data)} записей по лайкам")

            # Получаем предпочтения по избранному
            favorites_query = text(
                """
                SELECT
                    a.id as author_id,
                    a.name as author_name,
                    c.id as category_id,
                    c.name_categories as category_name,
                    t.id as tag_id,
                    t.name_tag as tag_name,
                    1 as interaction_count
                FROM favorites f
                JOIN books b ON f.book_id = b.id
                LEFT JOIN book_authors ba ON b.id = ba.book_id
                LEFT JOIN authors a ON ba.author_id = a.id
                LEFT JOIN books_categories bc ON b.id = bc.book_id
                LEFT JOIN categories c ON bc.category_id = c.id
                LEFT JOIN books_tags bt ON b.id = bt.book_id
                LEFT JOIN tags t ON bt.tag_id = t.id
                WHERE f.user_id = :user_id
            """
            )

            logger.info("Выполняем запрос для получения предпочтений по избранному")
            favorites_result = await self.db.execute(favorites_query, {"user_id": user_id})
            favorites_data = favorites_result.fetchall()
            logger.info(f"Получено {len(favorites_data)} записей по избранному")

            # Объединяем результаты
            preferences = {"authors": {}, "categories": {}, "tags": {}, "rated_books": rated_books}

            # Обрабатываем результаты оценок
            for row in ratings_data:
                if row.author_id:
                    preferences["authors"][row.author_id] = {
                        "name": row.author_name,
                        "weight": row.avg_rating * row.interaction_count,
                    }
                if row.category_id:
                    preferences["categories"][row.category_id] = {
                        "name": row.category_name,
                        "weight": row.avg_rating * row.interaction_count,
                    }
                if row.tag_id:
                    preferences["tags"][row.tag_id] = {
                        "name": row.tag_name,
                        "weight": row.avg_rating * row.interaction_count,
                    }

            # Добавляем лайки
            for row in likes_data:
                if row.author_id:
                    if row.author_id in preferences["authors"]:
                        preferences["authors"][row.author_id]["weight"] += 1
                    else:
                        preferences["authors"][row.author_id] = {"name": row.author_name, "weight": 1}
                if row.category_id:
                    if row.category_id in preferences["categories"]:
                        preferences["categories"][row.category_id]["weight"] += 1
                    else:
                        preferences["categories"][row.category_id] = {"name": row.category_name, "weight": 1}
                if row.tag_id:
                    if row.tag_id in preferences["tags"]:
                        preferences["tags"][row.tag_id]["weight"] += 1
                    else:
                        preferences["tags"][row.tag_id] = {"name": row.tag_name, "weight": 1}

            # Добавляем избранное
            for row in favorites_data:
                if row.author_id:
                    if row.author_id in preferences["authors"]:
                        preferences["authors"][row.author_id]["weight"] += 2  # Избранное имеет больший вес
                    else:
                        preferences["authors"][row.author_id] = {"name": row.author_name, "weight": 2}
                if row.category_id:
                    if row.category_id in preferences["categories"]:
                        preferences["categories"][row.category_id]["weight"] += 2
                    else:
                        preferences["categories"][row.category_id] = {"name": row.category_name, "weight": 2}
                if row.tag_id:
                    if row.tag_id in preferences["tags"]:
                        preferences["tags"][row.tag_id]["weight"] += 2
                    else:
                        preferences["tags"][row.tag_id] = {"name": row.tag_name, "weight": 2}

            logger.info(f"Успешно получены предпочтения для пользователя {user_id}")
            return preferences

        except Exception as e:
            logger.error(f"Ошибка при получении предпочтений пользователя: {str(e)}", exc_info=True)
            raise

    async def _get_content_recommendations(
        self,
        user_preferences: Dict[str, Any],
        limit: int,
        min_rating: float,
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        user_id: int,
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе предпочтений пользователя.
        """
        try:
            logger.info(f"Начинаем получение контентных рекомендаций для пользователя {user_id}")

            # Получаем предпочтения пользователя
            preferences = await self._get_user_preferences(user_id)

            if not any(preferences.values()):
                logger.info(f"Не найдено предпочтений для пользователя {user_id}")
                return []

            # Формируем SQL запрос для поиска книг на основе предпочтений
            query = text(
                """
                WITH user_preferences AS (
                    SELECT
                        a.id as author_id,
                        c.id as category_id,
                        t.id as tag_id,
                        AVG(r.rating) as avg_rating
                    FROM ratings r
                    JOIN books b ON r.book_id = b.id
                    LEFT JOIN book_authors ba ON b.id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.id
                    LEFT JOIN books_categories bc ON b.id = bc.book_id
                    LEFT JOIN categories c ON bc.category_id = c.id
                    LEFT JOIN books_tags bt ON b.id = bt.book_id
                    LEFT JOIN tags t ON bt.tag_id = t.id
                    WHERE r.user_id = :user_id
                    GROUP BY a.id, c.id, t.id
                ),
                book_scores AS (
                    SELECT
                        b.id,
                        b.title,
                        b.year,
                        COALESCE(AVG(r.rating), 0) as rating,
                        STRING_AGG(DISTINCT a.name, ', ') as author,
                        STRING_AGG(DISTINCT c.name_categories, ', ') as category,
                        SUM(
                            CASE
                                WHEN ba.author_id IN (SELECT author_id FROM user_preferences) THEN 1
                                ELSE 0
                            END +
                            CASE
                                WHEN bc.category_id IN (SELECT category_id FROM user_preferences) THEN 1
                                ELSE 0
                            END +
                            CASE
                                WHEN bt.tag_id IN (SELECT tag_id FROM user_preferences) THEN 1
                                ELSE 0
                            END
                        ) as match_score
                    FROM books b
                    LEFT JOIN ratings r ON b.id = r.book_id
                    LEFT JOIN book_authors ba ON b.id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.id
                    LEFT JOIN books_categories bc ON b.id = bc.book_id
                    LEFT JOIN categories c ON bc.category_id = c.id
                    LEFT JOIN books_tags bt ON b.id = bt.book_id
                    WHERE b.id NOT IN (
                        SELECT book_id FROM ratings WHERE user_id = :user_id
                    )
                    AND (COALESCE(:min_year, 0) = 0 OR CAST(b.year AS INTEGER) >= :min_year)
                    AND (COALESCE(:max_year, 9999) = 9999 OR CAST(b.year AS INTEGER) <= :max_year)
                    GROUP BY b.id, b.title, b.year
                )
                SELECT *
                FROM book_scores
                WHERE match_score > 0
                ORDER BY match_score DESC
                LIMIT :limit
            """
            )

            logger.info("Выполняем запрос для получения контентных рекомендаций")
            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "min_year": min_year or 0,
                    "max_year": max_year or 9999,
                    "min_ratings_count": min_ratings_count,
                    "limit": limit,
                },
            )
            books = result.fetchall()
            logger.info(f"Найдено {len(books)} книг на основе контентной фильтрации")

            recommendations = []
            for book in books:
                try:
                    recommendation = BookRecommendation(
                        id=book.id,
                        title=book.title,
                        author=book.author or "Неизвестный автор",
                        category=book.category or "Без категории",
                        rating=book.rating,
                        score=book.match_score,
                        reason=await self._get_recommendation_reason(book, preferences),
                        recommendation_type=RecommendationType.CONTENT,
                    )
                    recommendations.append(recommendation)
                except Exception as e:
                    logger.error(f"Ошибка при создании рекомендации для книги {book.id}: {str(e)}", exc_info=True)

            return recommendations

        except Exception as e:
            logger.error(f"Ошибка при получении контентных рекомендаций: {str(e)}", exc_info=True)
            return []

    async def _get_collaborative_recommendations(
        self,
        user_id: int,
        limit: int,
        min_rating: float,
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе оценок похожих пользователей.
        """
        try:
            logger.info(f"Начинаем получение коллаборативных рекомендаций для пользователя {user_id}")
            query = text(
                """
                WITH similar_users AS (
                    SELECT
                        r2.user_id,
                        COUNT(*) as common_ratings,
                        AVG(ABS(r1.rating - r2.rating)) as rating_diff
                    FROM ratings r1
                    JOIN ratings r2 ON r1.book_id = r2.book_id
                    WHERE r1.user_id = :user_id
                    AND r2.user_id != :user_id
                    GROUP BY r2.user_id
                    HAVING COUNT(*) >= 1  -- Минимальное количество общих оценок
                    ORDER BY rating_diff ASC
                    LIMIT 10
                ),
                book_ratings AS (
                    SELECT
                        b.*,
                        AVG(r2.rating) as avg_rating
                    FROM books b
                    JOIN ratings r ON b.id = r.book_id
                    JOIN ratings r2 ON b.id = r2.book_id
                    WHERE r.user_id IN (SELECT user_id FROM similar_users)
                    AND r2.user_id IN (SELECT user_id FROM similar_users)
                    AND r.rating >= :min_rating
                    AND b.id NOT IN (
                        SELECT book_id FROM ratings WHERE user_id = :user_id
                    )
                    GROUP BY b.id
                    HAVING COUNT(DISTINCT r2.user_id) >= 1  -- Минимальное количество оценок
                )
                SELECT DISTINCT *
                FROM book_ratings
                ORDER BY avg_rating DESC
                LIMIT :limit
            """
            )

            logger.info("Выполняем запрос для получения коллаборативных рекомендаций")
            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "min_rating": min_rating,
                    "min_ratings_count": min_ratings_count,
                    "limit": limit,
                },
            )
            books = result.fetchall()
            logger.info(f"Найдено {len(books)} книг на основе коллаборативной фильтрации")

            recommendations = []
            for book in books:
                try:
                    recommendation = BookRecommendation(
                        id=book.id,
                        title=book.title,
                        author=book.author,
                        category=book.category,
                        rating=book.rating,
                        score=book.avg_rating,
                        reason="Похожие пользователи высоко оценили эту книгу",
                    )
                    recommendations.append(recommendation)
                except Exception as e:
                    logger.error(f"Ошибка при создании рекомендации для книги {book.id}: {str(e)}", exc_info=True)

            return recommendations

        except Exception as e:
            logger.error(f"Ошибка при получении коллаборативных рекомендаций: {str(e)}", exc_info=True)
            return []

    async def _get_popularity_recommendations(
        self,
        limit: int,
        min_rating: float,
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        user_id: int,
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе популярности книг.
        """
        try:
            logger.info(f"Начинаем получение популярных рекомендаций для пользователя {user_id}")
            query = text(
                """
                WITH book_ratings AS (
                    SELECT
                        b.id,
                        b.title,
                        b.year,
                        COALESCE(AVG(r.rating), 0) as rating,
                        STRING_AGG(DISTINCT a.name, ', ') as author,
                        STRING_AGG(DISTINCT c.name_categories, ', ') as category,
                        COUNT(*) as rating_count
                    FROM books b
                    JOIN ratings r ON b.id = r.book_id
                    LEFT JOIN book_authors ba ON b.id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.id
                    LEFT JOIN books_categories bc ON b.id = bc.book_id
                    LEFT JOIN categories c ON bc.category_id = c.id
                    WHERE r.rating >= :min_rating
                    GROUP BY b.id, b.title, b.year
                    HAVING COUNT(*) >= 1
                )
                SELECT *
                FROM book_ratings
                WHERE id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                AND (COALESCE(:min_year, 0) = 0 OR CAST(year AS INTEGER) >= :min_year)
                AND (COALESCE(:max_year, 9999) = 9999 OR CAST(year AS INTEGER) <= :max_year)
                ORDER BY rating_count DESC
                LIMIT :limit
            """
            )

            logger.info("Выполняем запрос для получения популярных рекомендаций")
            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "min_rating": min_rating,
                    "min_year": min_year or 0,
                    "max_year": max_year or 9999,
                    "min_ratings_count": min_ratings_count,
                    "limit": limit,
                },
            )
            books = result.fetchall()
            logger.info(f"Найдено {len(books)} книг на основе популярности")

            recommendations = []
            for book in books:
                try:
                    recommendation = BookRecommendation(
                        id=book.id,
                        title=book.title,
                        author=book.author or "Неизвестный автор",
                        category=book.category or "Без категории",
                        rating=book.rating,
                        score=book.rating_count,
                        reason="Популярная книга среди пользователей",
                        recommendation_type=RecommendationType.POPULARITY,
                    )
                    recommendations.append(recommendation)
                except Exception as e:
                    logger.error(f"Ошибка при создании рекомендации для книги {book.id}: {str(e)}", exc_info=True)

            return recommendations

        except Exception as e:
            logger.error(f"Ошибка при получении популярных рекомендаций: {str(e)}", exc_info=True)
            return []

    async def _combine_recommendations(
        self,
        content_recommendations: List[BookRecommendation],
        collaborative_recommendations: List[BookRecommendation],
        limit: int,
    ) -> List[BookRecommendation]:
        """
        Объединить рекомендации от разных методов с учетом весов.
        """
        try:
            # Создаем словари для быстрого доступа к книгам
            content_dict = {book.id: book for book in content_recommendations}
            collaborative_dict = {book.id: book for book in collaborative_recommendations}

            # Объединяем все уникальные книги
            all_books = set(content_dict.keys()) | set(collaborative_dict.keys())

            # Вычисляем итоговую оценку для каждой книги
            book_scores = {}
            for book_id in all_books:
                content_score = 1.0 if book_id in content_dict else 0.0
                collaborative_score = 1.0 if book_id in collaborative_dict else 0.0

                # Взвешиваем оценки
                final_score = content_score * self.content_weight + collaborative_score * self.collaborative_weight
                book_scores[book_id] = final_score

            # Сортируем книги по итоговой оценке
            sorted_books = sorted(book_scores.items(), key=lambda x: x[1], reverse=True)

            # Формируем итоговый список рекомендаций
            recommendations = []
            for book_id, _ in sorted_books[:limit]:
                if book_id in content_dict:
                    recommendations.append(content_dict[book_id])
                else:
                    recommendations.append(collaborative_dict[book_id])

            return recommendations

        except Exception as e:
            logger.error(f"Ошибка при объединении рекомендаций: {str(e)}", exc_info=True)
            return []

    async def get_recommendation_stats(self, user_id: int) -> RecommendationStats:
        """
        Получить статистику для персональных рекомендаций.

        Args:
            user_id: ID пользователя

        Returns:
            RecommendationStats: Статистика рекомендаций
        """
        try:
            # Получаем предпочтения пользователя
            user_preferences = await self._get_user_preferences(user_id)

            # Статистика по оценкам пользователя
            ratings_stats_query = text(
                """
                SELECT
                    COUNT(*) as rated_books_count,
                    AVG(rating) as avg_rating
                FROM ratings
                WHERE user_id = :user_id
            """
            )

            # Общее количество книг в системе
            total_books_query = text(
                """
                SELECT COUNT(*) as total_books_count
                FROM books
            """
            )

            # Выполняем запросы
            ratings_result = await self.db.execute(ratings_stats_query, {"user_id": user_id})
            ratings_stats = ratings_result.fetchone()

            total_books_result = await self.db.execute(total_books_query)
            total_books = total_books_result.fetchone()

            # Выбираем топ-5 авторов, категорий и тегов
            authors = sorted(user_preferences.get("authors", {}).items(), key=lambda x: x[1]["weight"], reverse=True)[
                :5
            ]

            categories = sorted(
                user_preferences.get("categories", {}).items(), key=lambda x: x[1]["weight"], reverse=True
            )[:5]

            tags = sorted(user_preferences.get("tags", {}).items(), key=lambda x: x[1]["weight"], reverse=True)[:5]

            # Определяем готовность системы к предоставлению рекомендаций
            rated_books_count = ratings_stats.rated_books_count if ratings_stats else 0
            is_collaborative_ready = rated_books_count >= 5  # Минимум 5 оценок для коллаборативной фильтрации
            is_content_ready = (
                len(user_preferences.get("authors", {})) > 0
                or len(user_preferences.get("categories", {})) > 0
                or len(user_preferences.get("tags", {})) > 0
            )

            # Формируем статистику
            stats = RecommendationStats(
                user_id=user_id,
                rated_books_count=rated_books_count,
                total_books_count=total_books.total_books_count if total_books else 0,
                avg_rating=float(ratings_stats.avg_rating) if ratings_stats and ratings_stats.avg_rating else 0.0,
                favorite_authors=[a[1]["name"] for a in authors],
                favorite_categories=[c[1]["name"] for c in categories],
                favorite_tags=[t[1]["name"] for t in tags],
                is_collaborative_ready=is_collaborative_ready,
                is_content_ready=is_content_ready,
            )

            logger.info(f"Получена статистика рекомендаций для пользователя {user_id}")
            return stats

        except Exception as e:
            logger.error(f"Ошибка при получении статистики рекомендаций: {str(e)}", exc_info=True)
            # Возвращаем пустую статистику в случае ошибки
            return RecommendationStats(
                user_id=user_id,
                rated_books_count=0,
                total_books_count=0,
                avg_rating=0.0,
                favorite_authors=[],
                favorite_categories=[],
                favorite_tags=[],
                is_collaborative_ready=False,
                is_content_ready=False,
            )

    def get_cache_key(self, user_id, prefix, **kwargs):
        """
        Создает уникальный ключ для кэширования результата.

        Аргументы:
            user_id: ID пользователя
            prefix: Префикс ключа (например, 'recommendations', 'similar_users')
            **kwargs: Дополнительные параметры для включения в ключ

        Возвращает:
            Строка - ключ для кэша
        """
        # Создаем отсортированный список параметров для обеспечения консистентности ключей
        params = []
        for k in sorted(kwargs.keys()):
            v = kwargs[k]
            if v is not None:
                params.append(f"{k}:{v}")

        # Объединяем все в одну строку
        key = f"{prefix}:{user_id}"
        if params:
            key += f":{':'.join(params)}"

        return key

    def cache_result(self, key, data, expire_seconds=3600):
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
            # Преобразуем данные в JSON-совместимый формат с помощью jsonable_encoder
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
            self.redis_client.setex(key, expire_seconds, cached_value)
            logger.debug(f"Cached result with key: {key}, expires in {expire_seconds}s")
        except json.JSONDecodeError as e:
            logger.error(f"JSON serialization error while caching: {str(e)}")
        except Exception as e:
            logger.error(f"Error caching result: {str(e)}")
            # В случае ошибки просто продолжаем работу без кэширования

    def get_cached_result(self, key):
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
            cached = self.redis_client.get(key)
            if cached:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON deserialization error for cached data: {str(e)}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached result with key {key}: {str(e)}")
            return None
