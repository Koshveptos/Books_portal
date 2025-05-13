import json
from typing import Any, Dict, List, Optional

from core.logger_config import logger
from fastapi.encoders import jsonable_encoder
from models.book import (
    Book,
)
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

        Аргументы:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_year: Минимальный год издания
            max_year: Максимальный год издания
            min_ratings_count: Минимальное количество оценок
            recommendation_type: Тип рекомендаций
            cache: Использовать ли кэширование

        Возвращает:
            Список рекомендованных книг
        """
        # Проверяем наличие кэшированных результатов, если необходимо кэширование
        if cache:
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

        try:
            # Определяем стратегию рекомендаций в зависимости от типа
            user_preferences = await self._get_user_preferences(user_id)

            # Получаем рекомендации в соответствии с выбранной стратегией
            recommendations = []
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
                # Для гибридных рекомендаций объединяем результаты различных стратегий
                collaborative_recs = await self._get_collaborative_recommendations(
                    user_id=user_id,
                    limit=limit,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year,
                    min_ratings_count=min_ratings_count,
                )

                content_recs = await self._get_content_recommendations(
                    user_preferences=user_preferences,
                    limit=limit,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year,
                    min_ratings_count=min_ratings_count,
                    user_id=user_id,
                )

                popularity_recs = await self._get_popularity_recommendations(
                    limit=limit,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year,
                    min_ratings_count=min_ratings_count,
                    user_id=user_id,
                )

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
                    )
                    for item in sorted_recs[:limit]
                ]

            # Кэшируем результаты
            if cache and recommendations:
                self.cache_result(cache_key, recommendations, expire_seconds=3600)

            return recommendations
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {str(e)}")
            # В случае ошибки возвращаем пустой список
            return []

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

    async def _get_recommendation_reason(self, book: Book, user_preferences: Dict[str, Any]) -> str:
        """
        Получить причину рекомендации книги.
        """
        reasons = []

        # Проверяем совпадение с авторами
        if book.authors:
            for author in book.authors:
                if author.id in user_preferences.get("authors", {}):
                    reasons.append(f"Вам понравились книги автора {author.name}")
                    break

        # Проверяем совпадение с категориями
        if book.categories:
            for category in book.categories:
                if category.id in user_preferences.get("categories", {}):
                    reasons.append(f"Вам нравятся книги в категории {category.name}")
                    break

        # Проверяем совпадение с тегами
        if book.tags:
            for tag in book.tags:
                if tag.id in user_preferences.get("tags", {}):
                    reasons.append(f"Вам интересны книги с тегом {tag.name}")
                    break

        if not reasons:
            reasons.append("Похожие пользователи высоко оценили эту книгу")

        return " и ".join(reasons)

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
            # Получаем предпочтения по оценкам
            ratings_query = text(
                """
                SELECT
                    a.id as author_id,
                    a.name as author_name,
                    c.id as category_id,
                    c.name as category_name,
                    t.id as tag_id,
                    t.name as tag_name,
                    AVG(r.rating) as avg_rating,
                    COUNT(*) as interaction_count
                FROM ratings r
                JOIN books b ON r.book_id = b.id
                LEFT JOIN book_authors ba ON b.id = ba.book_id
                LEFT JOIN authors a ON ba.author_id = a.id
                LEFT JOIN book_categories bc ON b.id = bc.book_id
                LEFT JOIN categories c ON bc.category_id = c.id
                LEFT JOIN book_tags bt ON b.id = bt.book_id
                LEFT JOIN tags t ON bt.tag_id = t.id
                WHERE r.user_id = :user_id
                GROUP BY a.id, a.name, c.id, c.name, t.id, t.name
                HAVING AVG(r.rating) >= 3.0
            """
            )

            # Получаем предпочтения по лайкам
            likes_query = text(
                """
                SELECT
                    a.id as author_id,
                    a.name as author_name,
                    c.id as category_id,
                    c.name as category_name,
                    t.id as tag_id,
                    t.name as tag_name,
                    1 as interaction_count
                FROM likes l
                JOIN books b ON l.book_id = b.id
                LEFT JOIN book_authors ba ON b.id = ba.book_id
                LEFT JOIN authors a ON ba.author_id = a.id
                LEFT JOIN book_categories bc ON b.id = bc.book_id
                LEFT JOIN categories c ON bc.category_id = c.id
                LEFT JOIN book_tags bt ON b.id = bt.book_id
                LEFT JOIN tags t ON bt.tag_id = t.id
                WHERE l.user_id = :user_id
            """
            )

            # Получаем предпочтения по избранному
            favorites_query = text(
                """
                SELECT
                    a.id as author_id,
                    a.name as author_name,
                    c.id as category_id,
                    c.name as category_name,
                    t.id as tag_id,
                    t.name as tag_name,
                    1 as interaction_count
                FROM favorites f
                JOIN books b ON f.book_id = b.id
                LEFT JOIN book_authors ba ON b.id = ba.book_id
                LEFT JOIN authors a ON ba.author_id = a.id
                LEFT JOIN book_categories bc ON b.id = bc.book_id
                LEFT JOIN categories c ON bc.category_id = c.id
                LEFT JOIN book_tags bt ON b.id = bt.book_id
                LEFT JOIN tags t ON bt.tag_id = t.id
                WHERE f.user_id = :user_id
            """
            )

            # Выполняем запросы
            ratings_result = await self.db.execute(ratings_query, {"user_id": user_id})
            likes_result = await self.db.execute(likes_query, {"user_id": user_id})
            favorites_result = await self.db.execute(favorites_query, {"user_id": user_id})

            # Объединяем результаты
            preferences = {"authors": {}, "categories": {}, "tags": {}}

            # Обрабатываем результаты оценок
            for row in ratings_result:
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
            for row in likes_result:
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
            for row in favorites_result:
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

            return preferences

        except Exception as e:
            logger.error(f"Ошибка при получении предпочтений пользователя: {str(e)}", exc_info=True)
            return {"authors": {}, "categories": {}, "tags": {}}

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
                    LEFT JOIN book_categories bc ON b.id = bc.book_id
                    LEFT JOIN categories c ON bc.category_id = c.id
                    LEFT JOIN book_tags bt ON b.id = bt.book_id
                    LEFT JOIN tags t ON bt.tag_id = t.id
                    WHERE r.user_id = :user_id
                    GROUP BY a.id, c.id, t.id
                )
                SELECT DISTINCT b.*
                FROM books b
                LEFT JOIN book_authors ba ON b.id = ba.book_id
                LEFT JOIN book_categories bc ON b.id = bc.book_id
                LEFT JOIN book_tags bt ON b.id = bt.book_id
                WHERE (
                    ba.author_id IN (SELECT author_id FROM user_preferences)
                    OR bc.category_id IN (SELECT category_id FROM user_preferences)
                    OR bt.tag_id IN (SELECT tag_id FROM user_preferences)
                )
                AND b.id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                AND (:min_year IS NULL OR b.year >= :min_year)
                AND (:max_year IS NULL OR b.year <= :max_year)
                AND (
                    SELECT COUNT(*)
                    FROM ratings r
                    WHERE r.book_id = b.id
                ) >= :min_ratings_count
                ORDER BY (
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
                ) DESC
                LIMIT :limit
            """
            )

            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "min_year": min_year,
                    "max_year": max_year,
                    "min_ratings_count": min_ratings_count,
                    "limit": 50,
                },
            )
            books = result.fetchall()

            logger.info(f"Найдено {len(books)} книг на основе контентной фильтрации")
            return [BookRecommendation(**book) for book in books]

        except Exception as e:
            logger.error(f"Ошибка при получении контентных рекомендаций: {str(e)}", exc_info=True)
            return []

    async def _get_collaborative_recommendations(
        self, user_id: int, min_rating: float, min_year: Optional[int], max_year: Optional[int], min_ratings_count: int
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе оценок похожих пользователей.
        """
        try:
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
                    HAVING COUNT(*) >= 3
                    ORDER BY rating_diff ASC
                    LIMIT 10
                )
                SELECT DISTINCT b.*
                FROM books b
                JOIN ratings r ON b.id = r.book_id
                WHERE r.user_id IN (SELECT user_id FROM similar_users)
                AND r.rating >= :min_rating
                AND b.id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                AND (:min_year IS NULL OR b.year >= :min_year)
                AND (:max_year IS NULL OR b.year <= :max_year)
                AND (
                    SELECT COUNT(*)
                    FROM ratings r
                    WHERE r.book_id = b.id
                    AND r.user_id IN (SELECT user_id FROM similar_users)
                ) >= :min_ratings_count
                ORDER BY (
                    SELECT AVG(r2.rating)
                    FROM ratings r2
                    WHERE r2.book_id = b.id
                    AND r2.user_id IN (SELECT user_id FROM similar_users)
                ) DESC
                LIMIT :limit
            """
            )

            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "min_rating": min_rating,
                    "min_year": min_year,
                    "max_year": max_year,
                    "min_ratings_count": min_ratings_count,
                    "limit": 50,
                },
            )
            books = result.fetchall()

            logger.info(f"Найдено {len(books)} книг на основе коллаборативной фильтрации")
            return [BookRecommendation(**book) for book in books]

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
            query = text(
                """
                SELECT b.*
                FROM books b
                JOIN ratings r ON b.id = r.book_id
                WHERE r.user_id = :user_id
                AND r.rating >= :min_rating
                AND b.id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                AND (:min_year IS NULL OR b.year >= :min_year)
                AND (:max_year IS NULL OR b.year <= :max_year)
                AND (
                    SELECT COUNT(*)
                    FROM ratings r
                    WHERE r.book_id = b.id
                ) >= :min_ratings_count
                ORDER BY (
                    SELECT COUNT(*)
                    FROM ratings r
                    WHERE r.book_id = b.id
                ) DESC
                LIMIT :limit
            """
            )

            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "min_rating": min_rating,
                    "min_year": min_year,
                    "max_year": max_year,
                    "min_ratings_count": min_ratings_count,
                    "limit": limit,
                },
            )
            books = result.fetchall()

            logger.info(f"Найдено {len(books)} книг на основе популярности")
            return [BookRecommendation(**book) for book in books]

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
        Сохраняет результат в кэш.

        Аргументы:
            key: Ключ кэша
            data: Данные для кэширования (будут сериализованы в JSON)
            expire_seconds: Время жизни кэша в секундах

        Возвращает:
            bool: True если данные успешно сохранены, False в противном случае
        """
        if not self.redis_client:
            return False

        try:
            serialized = json.dumps(jsonable_encoder(data))
            return self.redis_client.setex(key, expire_seconds, serialized)
        except Exception as e:
            logger.error(f"Error caching result with key {key}: {str(e)}")
            return False

    def get_cached_result(self, key):
        """
        Получает результат из кэша.

        Аргументы:
            key: Ключ кэша

        Возвращает:
            Десериализованные данные или None, если кэш не найден
        """
        if not self.redis_client:
            return None

        try:
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached result with key {key}: {str(e)}")
            return None
