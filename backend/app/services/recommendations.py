import json
from typing import Any, Dict, List, Optional, Set

from fastapi.encoders import jsonable_encoder
from redis import Redis
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecommendationException
from app.core.logger_config import (
    log_critical_error,
    log_info,
    log_recommendation_error,
    logger,
)


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
    ) -> List[BookRecommendation]:
        """
        Получить персональные рекомендации книг для пользователя.
        """
        try:
            # Получаем ID книг, которые пользователь уже оценил
            try:
                rated_book_ids = await self._get_rated_book_ids(user_id)
                log_info(f"User {user_id} has rated {len(rated_book_ids)} books")
            except Exception as e:
                log_recommendation_error(e, user_id=user_id, context="getting rated books")
                rated_book_ids = set()

            # Инициализируем exclude_book_ids
            exclude_book_ids = rated_book_ids or {0}  # Используем {0} как безопасное значение по умолчанию
            log_info(f"Excluding {len(exclude_book_ids)} books from recommendations")

            # Получаем рекомендации в зависимости от типа
            recommendations = []
            if recommendation_type == RecommendationType.HYBRID:
                # Получаем рекомендации из разных источников
                try:
                    collaborative_recs = await self._get_collaborative_recommendations(
                        user_id, limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
                    )
                    log_info(f"Got {len(collaborative_recs)} collaborative recommendations")
                except Exception as e:
                    log_recommendation_error(e, user_id=user_id, context="getting collaborative recommendations")
                    collaborative_recs = []

                try:
                    content_recs = await self._get_content_recommendations(
                        user_id, limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
                    )
                    log_info(f"Got {len(content_recs)} content recommendations")
                except Exception as e:
                    log_recommendation_error(e, user_id=user_id, context="getting content recommendations")
                    content_recs = []

                try:
                    popularity_recs = await self._get_popularity_recommendations(
                        exclude_book_ids, min_ratings_count, min_rating, limit
                    )
                    log_info(f"Got {len(popularity_recs)} popularity recommendations")
                except Exception as e:
                    log_recommendation_error(e, user_id=user_id, context="getting popularity recommendations")
                    popularity_recs = []

                # Объединяем рекомендации
                recommendations = await self._combine_recommendations(
                    collaborative_recs, content_recs, popularity_recs, limit
                )
                log_info(f"Combined into {len(recommendations)} final recommendations")

            elif recommendation_type == RecommendationType.COLLABORATIVE:
                recommendations = await self._get_collaborative_recommendations(
                    user_id, limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
                )
            elif recommendation_type == RecommendationType.CONTENT:
                recommendations = await self._get_content_recommendations(
                    user_id, limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
                )
            elif recommendation_type == RecommendationType.POPULARITY:
                recommendations = await self._get_popularity_recommendations(
                    exclude_book_ids, min_ratings_count, min_rating, limit
                )

            # Если нет рекомендаций, возвращаем популярные книги
            if not recommendations:
                log_info(f"No recommendations found for user {user_id}, returning popular books")
                try:
                    recommendations = await self._get_popularity_recommendations(
                        exclude_book_ids, min_ratings_count, min_rating, limit
                    )
                    log_info(f"Successfully retrieved {len(recommendations)} popular books as fallback")
                except Exception as e:
                    log_recommendation_error(e, user_id=user_id, context="getting popular books as fallback")
                    recommendations = []

            return recommendations

        except Exception as e:
            log_critical_error(e, component="recommendations", context=f"get_user_recommendations for user {user_id}")
            # В случае критической ошибки пытаемся вернуть популярные книги
            try:
                log_info(f"Attempting to get popular books after critical error for user {user_id}")
                recommendations = await self._get_popularity_recommendations(
                    exclude_book_ids=exclude_book_ids or {0},
                    min_ratings_count=min_ratings_count,
                    min_rating=min_rating,
                    limit=limit,
                )
                log_info(f"Successfully retrieved {len(recommendations)} popular books after critical error")
                return recommendations
            except Exception as fallback_error:
                log_critical_error(fallback_error, component="recommendations", context="fallback to popular books")
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
        user_id: int,
        limit: int,
        min_rating: float,
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        try:
            logger.info(f"Начинаем получение контентных рекомендаций для пользователя {user_id}")

            # Проверяем, есть ли у пользователя оценки, лайки или избранное
            user_activity_query = text(
                """
                SELECT
                    COUNT(DISTINCT r.book_id) as rated_books,
                    COUNT(DISTINCT l.book_id) as liked_books,
                    COUNT(DISTINCT f.book_id) as favorited_books
                FROM users u
                LEFT JOIN ratings r ON u.id = r.user_id
                LEFT JOIN likes l ON u.id = l.user_id
                LEFT JOIN favorites f ON u.id = f.user_id
                WHERE u.id = :user_id
            """
            )

            result = await self.db.execute(user_activity_query, {"user_id": user_id})
            activity = result.fetchone()
            total_activity = (activity.rated_books or 0) + (activity.liked_books or 0) + (activity.favorited_books or 0)

            logger.info(
                f"У пользователя {user_id} найдено {total_activity} активностей (оценки: {activity.rated_books}, лайки: {activity.liked_books}, избранное: {activity.favorited_books})"
            )

            if total_activity < 1:
                logger.info(
                    f"У пользователя {user_id} недостаточно активностей ({total_activity}) для контентных рекомендаций"
                )
                return []

            # Проверяем, что exclude_book_ids не пустой
            if not exclude_book_ids:
                exclude_book_ids = {0}
                logger.info("Используем {0} как значение по умолчанию для exclude_book_ids")

            # Преобразуем множество в список для использования в SQL
            exclude_list = list(exclude_book_ids)

            query = text(
                """
                WITH user_preferences AS (
                    SELECT
                        b.id as book_id,
                        b.title,
                        CASE
                            WHEN b.year ~ '^[0-9]{4}$' THEN CAST(b.year AS INTEGER)
                            ELSE NULL
                        END as year,
                        b.cover,
                        STRING_AGG(DISTINCT a.name, ', ') as author_names,
                        COALESCE(AVG(r.rating), 0) as avg_rating,
                        COUNT(DISTINCT l.book_id) as likes_count,
                        COUNT(DISTINCT f.book_id) as favorites_count
                    FROM books b
                    LEFT JOIN ratings r ON b.id = r.book_id AND r.user_id = :user_id
                    LEFT JOIN likes l ON b.id = l.book_id AND l.user_id = :user_id
                    LEFT JOIN favorites f ON b.id = f.book_id AND f.user_id = :user_id
                    LEFT JOIN book_authors ba ON b.id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.id
                    WHERE r.id IS NOT NULL OR l.book_id IS NOT NULL OR f.book_id IS NOT NULL
                    GROUP BY b.id, b.title, b.year, b.cover
                ),
                similar_books AS (
                    SELECT
                        b.id,
                        b.title,
                        CASE
                            WHEN b.year ~ '^[0-9]{4}$' THEN CAST(b.year AS INTEGER)
                            ELSE NULL
                        END as year,
                        b.cover,
                        STRING_AGG(DISTINCT a.name, ', ') as author_names,
                        COALESCE(AVG(r.rating), 0) as avg_rating,
                        COUNT(r.id) as ratings_count,
                        COUNT(DISTINCT CASE WHEN r.user_id = :user_id THEN r.user_id END) as user_rating_count
                    FROM books b
                    LEFT JOIN ratings r ON b.id = r.book_id
                    LEFT JOIN book_authors ba ON b.id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.id
                    WHERE b.id != ALL(:exclude_list)
                    GROUP BY b.id, b.title, b.year, b.cover
                    HAVING COUNT(r.id) >= :min_ratings_count
                    AND COALESCE(AVG(r.rating), 0) >= :min_rating
                )
                SELECT *
                FROM similar_books
                ORDER BY avg_rating DESC, ratings_count DESC
                LIMIT :limit
            """
            )

            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "min_rating": 2.0,
                    "min_ratings_count": 1,
                    "exclude_list": exclude_list,
                    "limit": limit,
                },
            )
            rows = result.all()
            logger.info(f"Найдено {len(rows)} книг на основе контентной фильтрации")

            recommendations = []
            for row in rows:
                try:
                    normalized_score = min(row.avg_rating / 5.0, 1.0)
                    author_names = row.author_names.split(", ") if row.author_names else []
                    author = author_names[0] if author_names else "Неизвестный автор"

                    recommendations.append(
                        BookRecommendation(
                            id=row.id,
                            book_id=row.id,
                            title=row.title,
                            author=author,
                            author_names=author_names,
                            year=row.year if row.year is not None else 0,
                            cover=row.cover,
                            score=normalized_score,
                            reason=f"Похожие пользователи высоко оценили эту книгу (рейтинг {row.avg_rating:.1f}, {row.ratings_count} оценок)",
                            recommendation_type=RecommendationType.CONTENT,
                        )
                    )
                except Exception as e:
                    logger.error(f"Ошибка при создании рекомендации для книги {row.id}: {str(e)}", exc_info=True)
                    continue

            logger.info(f"Успешно создано {len(recommendations)} контентных рекомендаций")
            return recommendations

        except Exception as e:
            logger.error(f"Критическая ошибка при получении контентных рекомендаций: {str(e)}", exc_info=True)
            return []

    async def _get_collaborative_recommendations(
        self,
        user_id: int,
        limit: int,
        min_rating: float,
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        try:
            logger.info(f"Начинаем получение коллаборативных рекомендаций для пользователя {user_id}")

            # Проверяем, есть ли у пользователя оценки
            ratings_check_query = text(
                """
                SELECT COUNT(*) as rating_count
                FROM ratings
                WHERE user_id = :user_id
            """
            )

            result = await self.db.execute(ratings_check_query, {"user_id": user_id})
            rating_count = result.scalar()
            logger.info(f"У пользователя {user_id} найдено {rating_count} оценок")

            if rating_count < 2:  # Уменьшаем с min_ratings_count до 2
                logger.info(
                    f"У пользователя {user_id} недостаточно оценок ({rating_count}) для коллаборативных рекомендаций"
                )
                return []

            # Проверяем, что exclude_book_ids не пустой
            if not exclude_book_ids:
                exclude_book_ids = {0}
                logger.info("Используем {0} как значение по умолчанию для exclude_book_ids")

            # Преобразуем множество в список для использования в SQL
            exclude_list = list(exclude_book_ids)

            query = text(
                """
                WITH similar_users AS (
                    SELECT
                        r2.user_id,
                        COUNT(*) as common_ratings,
                        AVG(ABS(r1.rating - r2.rating)) as rating_diff,
                        CORR(r1.rating, r2.rating) as correlation
                    FROM ratings r1
                    JOIN ratings r2 ON r1.book_id = r2.book_id
                    WHERE r1.user_id = :user_id
                    AND r2.user_id != :user_id
                    GROUP BY r2.user_id
                    HAVING COUNT(*) >= :min_common_ratings
                    ORDER BY correlation DESC NULLS LAST, rating_diff ASC
                    LIMIT 10
                ),
                recommended_books AS (
                    SELECT
                        b.id,
                        b.title,
                        b.year,
                        b.cover,
                        COALESCE(AVG(r.rating), 0) as avg_rating,
                        COUNT(r.id) as ratings_count,
                        STRING_AGG(DISTINCT a.name, ', ') as author_names
                    FROM books b
                    JOIN ratings r ON b.id = r.book_id
                    LEFT JOIN book_authors ba ON b.id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.id
                    WHERE r.user_id IN (SELECT user_id FROM similar_users)
                    AND b.id != ALL(:exclude_list)
                    GROUP BY b.id, b.title, b.year, b.cover
                    HAVING COUNT(r.id) >= :min_ratings_count
                    AND COALESCE(AVG(r.rating), 0) >= :min_rating
                )
                SELECT *
                FROM recommended_books
                ORDER BY avg_rating DESC, ratings_count DESC
                LIMIT :limit
            """
            )

            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "min_rating": 2.0,  # Уменьшаем с min_rating до 2.0
                    "min_ratings_count": 2,  # Уменьшаем с min_ratings_count до 2
                    "min_common_ratings": 2,  # Уменьшаем с 3 до 2
                    "exclude_list": exclude_list,
                    "limit": limit,
                },
            )
            rows = result.all()
            logger.info(f"Найдено {len(rows)} книг на основе коллаборативной фильтрации")

            recommendations = []
            for row in rows:
                try:
                    normalized_score = min(row.avg_rating / 5.0, 1.0)
                    author_names = row.author_names.split(", ") if row.author_names else []
                    author = author_names[0] if author_names else "Неизвестный автор"

                    recommendations.append(
                        BookRecommendation(
                            id=row.id,
                            book_id=row.id,
                            title=row.title,
                            author=author,
                            author_names=author_names,
                            year=row.year,
                            cover=row.cover,
                            score=normalized_score,
                            reason=f"Похожие пользователи высоко оценили эту книгу (рейтинг {row.avg_rating:.1f}, {row.ratings_count} оценок)",
                            recommendation_type=RecommendationType.COLLABORATIVE,
                        )
                    )
                except Exception as e:
                    logger.error(f"Ошибка при создании рекомендации для книги {row.id}: {str(e)}", exc_info=True)
                    continue

            logger.info(f"Успешно создано {len(recommendations)} коллаборативных рекомендаций")
            return recommendations

        except Exception as e:
            logger.error(f"Критическая ошибка при получении коллаборативных рекомендаций: {str(e)}", exc_info=True)
            return []

    async def _get_popularity_recommendations(
        self,
        excluded_book_ids: List[int],
        min_ratings_count: int = 1,
        min_rating: float = 2.0,
        limit: int = 10,
    ) -> List[BookRecommendation]:
        """
        Получить популярные книги на основе рейтингов, лайков и избранного.
        """
        try:
            log_info("Начинаем получение популярных рекомендаций")

            query = """
                WITH book_stats AS (
                    SELECT
                        b.id,
                        b.title,
                        CASE
                            WHEN b.year ~ '^[0-9]{4}$' THEN CAST(b.year AS INTEGER)
                            ELSE NULL
                        END as year,
                        b.cover,
                        COALESCE(AVG(r.rating), 0) as avg_rating,
                        COUNT(DISTINCT r.id) as ratings_count,
                        COUNT(DISTINCT l.book_id) as likes_count,
                        COUNT(DISTINCT f.book_id) as favorites_count,
                        STRING_AGG(DISTINCT a.name, ', ') as author_names,
                        (
                            COALESCE(AVG(r.rating), 0) * 0.5 +
                            (COUNT(DISTINCT l.book_id) * 0.3) +
                            (COUNT(DISTINCT f.book_id) * 0.2)
                        ) as popularity_score
                    FROM books b
                    LEFT JOIN ratings r ON b.id = r.book_id
                    LEFT JOIN likes l ON b.id = l.book_id
                    LEFT JOIN favorites f ON b.id = f.book_id
                    LEFT JOIN book_authors ba ON b.id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.id
                    WHERE b.id != ALL(:excluded_ids)
                    GROUP BY b.id, b.title, b.year, b.cover
                    HAVING COUNT(DISTINCT r.id) >= :min_ratings_count
                    AND COALESCE(AVG(r.rating), 0) >= :min_rating
                )
                SELECT *
                FROM book_stats
                ORDER BY popularity_score DESC, avg_rating DESC, ratings_count DESC
                LIMIT :limit
            """

            result = await self.db.execute(
                text(query),
                {
                    "excluded_ids": excluded_book_ids,
                    "min_ratings_count": min_ratings_count,
                    "min_rating": min_rating,
                    "limit": limit,
                },
            )

            books = result.mappings().all()

            recommendations = []
            for book in books:
                author_names = book["author_names"].split(", ") if book["author_names"] else []
                author = author_names[0] if author_names else "Неизвестный автор"

                recommendations.append(
                    BookRecommendation(
                        id=book["id"],
                        book_id=book["id"],
                        title=book["title"],
                        author=author,
                        author_names=author_names,
                        year=book["year"],
                        cover=book["cover"],
                        score=float(book["popularity_score"]),
                        reason=(
                            f"Популярная книга с рейтингом {book['avg_rating']:.1f}, "
                            f"{book['ratings_count']} оценками, "
                            f"{book['likes_count']} лайками и "
                            f"{book['favorites_count']} добавлениями в избранное"
                        ),
                        recommendation_type=RecommendationType.POPULARITY,
                    )
                )

            log_info(f"Got {len(recommendations)} popularity recommendations")
            return recommendations

        except Exception as e:
            log_critical_error(e, "Критическая ошибка при получении популярных рекомендаций")
            return []

    async def _get_random_books(
        self,
        limit: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        """
        Получить случайные книги для дополнения рекомендаций.
        """
        try:
            query = text(
                """
                SELECT
                    b.id,
                    b.title,
                    CASE
                        WHEN b.year ~ '^[0-9]{4}$' THEN CAST(b.year AS INTEGER)
                        ELSE NULL
                    END as year,
                    b.cover,
                    STRING_AGG(DISTINCT a.name, ', ') as author_names
                FROM books b
                LEFT JOIN book_authors ba ON b.id = ba.book_id
                LEFT JOIN authors a ON ba.author_id = a.id
                WHERE b.id != ALL(:exclude_ids)
                GROUP BY b.id, b.title, b.year, b.cover
                ORDER BY RANDOM()
                LIMIT :limit
            """
            )

            result = await self.db.execute(query, {"exclude_ids": list(exclude_book_ids), "limit": limit})

            books = result.mappings().all()

            recommendations = []
            for book in books:
                author_names = book["author_names"].split(", ") if book["author_names"] else []
                author = author_names[0] if author_names else "Неизвестный автор"

                recommendations.append(
                    BookRecommendation(
                        id=book["id"],
                        book_id=book["id"],
                        title=book["title"],
                        author=author,
                        author_names=author_names,
                        year=book["year"],
                        cover=book["cover"],
                        score=0.5,  # Средний score для случайных книг
                        reason="Случайная рекомендация",
                        recommendation_type=RecommendationType.RANDOM,
                    )
                )

            return recommendations
        except Exception as e:
            logger.error(f"Ошибка при получении случайных книг: {str(e)}", exc_info=True)
            return []

    async def _combine_recommendations(
        self,
        collaborative: List[BookRecommendation],
        content: List[BookRecommendation],
        popularity: List[BookRecommendation],
        limit: int,
    ) -> List[BookRecommendation]:
        try:
            logger.info(
                f"Начинаем объединение рекомендаций: коллаборативных={len(collaborative)}, "
                f"контентных={len(content)}, популярных={len(popularity)}"
            )

            # Создаем словарь для хранения уникальных рекомендаций
            unique_recommendations = {}

            # Добавляем рекомендации в порядке приоритета
            for rec in collaborative:
                try:
                    if rec.id not in unique_recommendations:
                        unique_recommendations[rec.id] = rec
                except Exception as e:
                    logger.error(f"Ошибка при добавлении коллаборативной рекомендации: {str(e)}", exc_info=True)
                    continue

            for rec in content:
                try:
                    if rec.id not in unique_recommendations:
                        unique_recommendations[rec.id] = rec
                except Exception as e:
                    logger.error(f"Ошибка при добавлении контентной рекомендации: {str(e)}", exc_info=True)
                    continue

            # Преобразуем словарь в список
            recommendations = list(unique_recommendations.values())

            # Если рекомендаций меньше limit, добавляем популярные книги
            if len(recommendations) < limit:
                try:
                    # Получаем ID уже рекомендованных книг
                    existing_ids = {rec.id for rec in recommendations}

                    # Добавляем популярные книги только если не хватает рекомендаций
                    for rec in popularity:
                        if rec.id not in existing_ids and len(recommendations) < limit:
                            recommendations.append(rec)
                            existing_ids.add(rec.id)

                    logger.info(
                        f"Добавлено {len(recommendations) - len(unique_recommendations)} популярных книг для достижения лимита в {limit} рекомендаций"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при добавлении популярных книг: {str(e)}", exc_info=True)

            # Если все еще не хватает рекомендаций до 15, добавляем случайные книги
            if len(recommendations) < 15:
                try:
                    # Получаем ID уже рекомендованных книг
                    existing_ids = {rec.id for rec in recommendations}

                    # Получаем случайные книги
                    random_books = await self._get_random_books(
                        limit=15 - len(recommendations), exclude_book_ids=existing_ids
                    )

                    recommendations.extend(random_books)
                    logger.info(f"Добавлено {len(random_books)} случайных книг для достижения лимита в 15 рекомендаций")
                except Exception as e:
                    logger.error(f"Ошибка при добавлении случайных книг: {str(e)}", exc_info=True)

            # Сортируем рекомендации:
            # 1. Сначала по типу рекомендации (коллаборативные и контентные идут первыми)
            # 2. Затем по score внутри каждого типа
            recommendations.sort(
                key=lambda x: (
                    0 if x.recommendation_type in [RecommendationType.COLLABORATIVE, RecommendationType.CONTENT] else 1,
                    -x.score,  # Отрицательный score для сортировки по убыванию
                )
            )

            # Возвращаем ограниченное количество рекомендаций
            result = recommendations[:limit]
            logger.info(f"Успешно объединены рекомендации, итоговое количество: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"Критическая ошибка при объединении рекомендаций: {str(e)}", exc_info=True)
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

    async def _get_rated_book_ids(self, user_id: int) -> List[int]:
        """Получить список ID книг, которые пользователь оценил"""
        query = text(
            """
            SELECT book_id
            FROM ratings
            WHERE user_id = :user_id
        """
        )
        result = await self.db.execute(query, {"user_id": user_id})
        return [row[0] for row in result.all()]

    async def _get_liked_book_ids(self, user_id: int) -> List[int]:
        """Получить список ID книг, которые пользователь лайкнул"""
        query = text(
            """
            SELECT book_id
            FROM likes
            WHERE user_id = :user_id
        """
        )
        result = await self.db.execute(query, {"user_id": user_id})
        return [row[0] for row in result.all()]

    async def _get_favorited_book_ids(self, user_id: int) -> List[int]:
        """Получить список ID книг, которые пользователь добавил в избранное"""
        query = text(
            """
            SELECT book_id
            FROM favorites
            WHERE user_id = :user_id
        """
        )
        result = await self.db.execute(query, {"user_id": user_id})
        return [row[0] for row in result.all()]


async def get_recommendation_stats_from_db(user_id: int, db: AsyncSession) -> RecommendationStats:
    """Получение статистики рекомендаций из базы данных"""
    try:
        recommendation_service = RecommendationService(db, None)
        return await recommendation_service.get_recommendation_stats(user_id=user_id)
    except Exception as e:
        logger.error(f"Error getting recommendation stats from DB: {str(e)}", exc_info=True)
        raise RecommendationException("Ошибка при получении статистики рекомендаций")


async def get_similar_users_from_db(user_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
    """Получение похожих пользователей из базы данных"""
    try:
        recommendation_service = RecommendationService(db, None)
        return await recommendation_service.get_similar_users(user_id=user_id)
    except Exception as e:
        logger.error(f"Error getting similar users from DB: {str(e)}", exc_info=True)
        raise RecommendationException("Ошибка при получении похожих пользователей")


async def get_author_recommendations_from_db(user_id: int, db: AsyncSession) -> List[BookRecommendation]:
    """Получение рекомендаций по авторам из базы данных"""
    try:
        recommendation_service = RecommendationService(db, None)
        user_preferences = await recommendation_service._get_user_preferences(user_id)
        return await recommendation_service._get_author_recommendations(
            user_preferences=user_preferences,
            limit=10,
            min_rating=3.0,
            min_year=None,
            max_year=None,
            min_ratings_count=5,
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Error getting author recommendations from DB: {str(e)}", exc_info=True)
        raise RecommendationException("Ошибка при получении рекомендаций по авторам")


async def get_category_recommendations_from_db(user_id: int, db: AsyncSession) -> List[BookRecommendation]:
    """Получение рекомендаций по категориям из базы данных"""
    try:
        recommendation_service = RecommendationService(db, None)
        user_preferences = await recommendation_service._get_user_preferences(user_id)
        return await recommendation_service._get_category_recommendations(
            user_preferences=user_preferences,
            limit=10,
            min_rating=3.0,
            min_year=None,
            max_year=None,
            min_ratings_count=5,
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Error getting category recommendations from DB: {str(e)}", exc_info=True)
        raise RecommendationException("Ошибка при получении рекомендаций по категориям")


async def get_tag_recommendations_from_db(user_id: int, db: AsyncSession) -> List[BookRecommendation]:
    """Получение рекомендаций по тегам из базы данных"""
    try:
        recommendation_service = RecommendationService(db, None)
        user_preferences = await recommendation_service._get_user_preferences(user_id)
        return await recommendation_service._get_tag_recommendations(
            user_preferences=user_preferences,
            limit=10,
            min_rating=3.0,
            min_year=None,
            max_year=None,
            min_ratings_count=5,
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Error getting tag recommendations from DB: {str(e)}", exc_info=True)
        raise RecommendationException("Ошибка при получении рекомендаций по тегам")
