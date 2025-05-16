import json
from typing import Any, Dict, List, Optional

from core.logger_config import logger
from fastapi.encoders import jsonable_encoder
from models.book import Book, Rating
from redis import Redis
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased


class RecommendationService:
    """Гибридная рекомендательная система, сочетающая коллаборативную и контентную фильтрацию."""

    def __init__(self, db: AsyncSession, redis_client: Optional[Redis] = None):
        self.db = db
        self.redis_client = redis_client
        self.content_weight = 0.4
        self.collaborative_weight = 0.6
        self.cache_ttl = 600

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
        logger.info(
            f"Запуск рекомендаций для user_id={user_id}, type={recommendation_type}, "
            f"limit={limit}, min_rating={min_rating}, min_ratings_count={min_ratings_count}, "
            f"min_year={min_year}, max_year={max_year}, cache={cache}"
        )
        try:
            # Ограничиваем максимальное количество рекомендаций
            if limit > 20:
                logger.warning(f"Ограничение рекомендаций с {limit} до 20")
                limit = 20

            # Проверяем наличие кэшированных результатов
            if cache and self.redis_client:
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
                    logger.info(f"Использование кэшированных рекомендаций для user_id={user_id}")
                    return [BookRecommendation(**item) for item in cached_recommendations]

            # Получаем рекомендации
            recommendations = []
            async with self.db.begin():
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
                    elif recommendation_type == RecommendationType.CONTENT:
                        user_preferences = await self._get_user_preferences(user_id)
                        logger.debug(f"Предпочтения пользователя {user_id}: {user_preferences}")
                        recommendations = await self._get_content_recommendations(
                            user_preferences=user_preferences,
                            limit=limit,
                            min_rating=min_rating,
                            min_year=min_year,
                            max_year=max_year,
                            min_ratings_count=min_ratings_count,
                            user_id=user_id,
                        )
                    else:  # HYBRID
                        collaborative_recs = await self._get_collaborative_recommendations(
                            user_id=user_id,
                            limit=limit,
                            min_rating=min_rating,
                            min_year=min_year,
                            max_year=max_year,
                            min_ratings_count=min_ratings_count,
                        )
                        user_preferences = await self._get_user_preferences(user_id)
                        logger.debug(f"Предпочтения пользователя {user_id}: {user_preferences}")
                        content_recs = await self._get_content_recommendations(
                            user_preferences=user_preferences,
                            limit=limit,
                            min_rating=min_rating,
                            min_year=min_year,
                            max_year=max_year,
                            min_ratings_count=min_ratings_count,
                            user_id=user_id,
                        )
                        logger.debug(
                            f"Коллаборативные рекомендации: {len(collaborative_recs)} книг, "
                            f"Контентные рекомендации: {len(content_recs)} книг"
                        )
                        recommendations = await self._combine_recommendations(
                            content_recommendations=content_recs,
                            collaborative_recommendations=collaborative_recs,
                            limit=limit,
                        )
                except Exception as e:
                    logger.error(f"Ошибка в транзакции для user_id={user_id}: {str(e)}", exc_info=True)
                    await self.db.rollback()
                    raise

            # Ограничиваем размер ответа
            if len(recommendations) > limit:
                logger.debug(f"Усечение рекомендаций с {len(recommendations)} до {limit}")
                recommendations = recommendations[:limit]

            # Проверяем размер сериализованного ответа
            json_data = jsonable_encoder(recommendations)
            serialized_data = json.dumps(json_data)
            if len(serialized_data.encode("utf-8")) > 1024 * 1024:  # 1MB
                logger.warning(
                    f"Размер ответа слишком большой ({len(serialized_data.encode('utf-8'))} байт), усечение до 5"
                )
                recommendations = recommendations[:5]

            # Кэшируем результаты
            if cache and recommendations and self.redis_client:
                logger.debug(f"Кэширование рекомендаций для user_id={user_id}")
                self.cache_result(cache_key, recommendations)

            logger.info(f"Возвращено {len(recommendations)} рекомендаций для user_id={user_id}")
            return recommendations

        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций для user_id={user_id}: {str(e)}", exc_info=True)
            return []  # Возвращаем пустой список, роутер обработает 204

    async def get_similar_users(
        self, user_id: int, limit: int = 10, min_common_ratings: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Получить список похожих пользователей.
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

        if book.authors:
            for author in book.authors:
                if author.id in user_preferences.get("authors", {}):
                    reasons.append(f"Вам понравились книги автора {author.name}")
                    break

        if book.categories:
            for category in book.categories:
                if category.id in user_preferences.get("categories", {}):
                    reasons.append(f"Вам нравятся книги в категории {category.name}")
                    break

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
        min_year: Optional[int],  # Оставляем для совместимости, но не используем
        max_year: Optional[int],  # Оставляем для совместимости, но не используем
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
                ORDER BY b.id DESC
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
        min_year: Optional[int],  # Оставляем для совместимости, но не используем
        max_year: Optional[int],  # Оставляем для совместимости, но не используем
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
                JOIN books_categories bc ON b.id = bc.book_id
                WHERE bc.category_id = ANY(:category_ids)
                AND b.id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                ORDER BY b.id DESC
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
        min_year: Optional[int],  # Оставляем для совместимости, но не используем
        max_year: Optional[int],  # Оставляем для совместимости, но не используем
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
                JOIN books_tags bt ON b.id = bt.book_id
                WHERE bt.tag_id = ANY(:tag_ids)
                AND b.id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                ORDER BY b.id DESC
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
            preferences = {"authors": {}, "categories": {}, "tags": {}}

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

            # Выполняем запросы без создания новых транзакций
            ratings_result = await self.db.execute(ratings_query, {"user_id": user_id})
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

            likes_result = await self.db.execute(likes_query, {"user_id": user_id})
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

            favorites_result = await self.db.execute(favorites_query, {"user_id": user_id})
            for row in favorites_result:
                if row.author_id:
                    if row.author_id in preferences["authors"]:
                        preferences["authors"][row.author_id]["weight"] += 2
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

            logger.debug(f"Preferences for user {user_id}: {preferences}")
            return preferences

        except Exception as e:
            logger.error(f"Ошибка при получении предпочтений пользователя: {str(e)}", exc_info=True)
            return {"authors": {}, "categories": {}, "tags": {}}

    async def _get_content_recommendations(
        self,
        user_preferences: Dict[str, Any],
        limit: int,
        min_rating: float,
        min_year: Optional[int],  # Оставляем для совместимости, но не используем
        max_year: Optional[int],  # Оставляем для совместимости, но не используем
        min_ratings_count: int,
        user_id: int,
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе предпочтений пользователя.
        """
        try:
            if not any(user_preferences.values()):
                logger.info(f"Не найдено предпочтений для пользователя {user_id}")
                return []

            logger.debug(
                f"Параметры для контентных рекомендаций: user_id={user_id}, "
                f"limit={limit}, min_rating={min_rating}, min_year={min_year}, "
                f"max_year={max_year}, min_ratings_count={min_ratings_count}"
            )

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
                )
                SELECT DISTINCT b.*,
                    (
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
                LEFT JOIN book_authors ba ON b.id = ba.book_id
                LEFT JOIN books_categories bc ON b.id = bc.book_id
                LEFT JOIN books_tags bt ON b.id = bt.book_id
                WHERE (
                    ba.author_id IN (SELECT author_id FROM user_preferences)
                    OR bc.category_id IN (SELECT category_id FROM user_preferences)
                    OR bt.tag_id IN (SELECT tag_id FROM user_preferences)
                )
                AND b.id NOT IN (
                    SELECT book_id FROM ratings WHERE user_id = :user_id
                )
                AND (
                    SELECT COUNT(*)
                    FROM ratings r
                    WHERE r.book_id = b.id
                ) >= :min_ratings_count
                ORDER BY match_score DESC
                LIMIT :limit
                """
            )

            params = {
                "user_id": user_id,
                "min_ratings_count": min_ratings_count,
                "limit": limit,
            }
            logger.debug(f"Параметры SQL-запроса: {params}")

            result = await self.db.execute(query, params)
            books = result.fetchall()

            logger.info(f"Найдено {len(books)} книг на основе контентной фильтрации для user_id={user_id}")
            if books:
                logger.debug(f"Рекомендованные книги: {[book.id for book in books]}")
            else:
                logger.warning(
                    f"Контентные рекомендации не найдены для user_id={user_id}. "
                    f"Проверяйте наличие книг с author_id={list(user_preferences.get('authors', {}).keys())}, "
                    f"category_id={list(user_preferences.get('categories', {}).keys())}, "
                    f"tag_id={list(user_preferences.get('tags', {}).keys())} и min_ratings_count={min_ratings_count}"
                )

            return [BookRecommendation(**book) for book in books]

        except Exception as e:
            logger.error(f"Ошибка при получении контентных рекомендаций для user_id={user_id}: {str(e)}", exc_info=True)
            return []

    async def _get_collaborative_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        min_rating: float = 3.0,
        min_year: Optional[int] = None,  # Оставляем для совместимости, но не используем
        max_year: Optional[int] = None,  # Оставляем для совместимости, но не используем
        min_ratings_count: int = 2,  # Вернуть 5 после дебага
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе оценок похожих пользователей.
        Реализация через ORM.
        """
        try:
            logger.debug(
                f"Параметры для коллаборативных рекомендаций: user_id={user_id}, "
                f"limit={limit}, min_rating={min_rating}, min_year={min_year}, "
                f"max_year={max_year}, min_ratings_count={min_ratings_count}"
            )

            rated_books_subquery = select(Rating.book_id).where(Rating.user_id == user_id).subquery()

            # Логируем оцененные книги
            rated_books_result = await self.db.execute(select(rated_books_subquery.c.book_id))
            rated_books = rated_books_result.scalars().all()
            logger.debug(f"Оцененные книги user_id={user_id}: {rated_books}")

            r1 = aliased(Rating)
            r2 = aliased(Rating)

            similar_users_subquery = (
                select(r2.user_id)
                .join(r1, r1.book_id == r2.book_id)
                .where(r1.user_id == user_id, r2.user_id != user_id)
                .group_by(r2.user_id)
                .having(func.count(r1.id) >= 1)  # Вернуть 3 после дебага
                .order_by(func.avg(func.abs(r1.rating - r2.rating)).asc())
                .limit(10)
                .subquery()
            )

            # Логируем похожих пользователей
            similar_users_result = await self.db.execute(select(similar_users_subquery.c.user_id))
            similar_users = similar_users_result.scalars().all()
            logger.info(f"Найдено {len(similar_users)} похожих пользователей для user_id={user_id}: {similar_users}")
            if not similar_users:
                logger.warning(
                    f"Похожие пользователи не найдены для user_id={user_id}. "
                    f"Проверьте наличие общих оценок с другими пользователями."
                )

            rating_alias = aliased(Rating)
            book_alias = aliased(Book)

            query = (
                select(book_alias, func.avg(rating_alias.rating).label("avg_rating"))
                .join(rating_alias, book_alias.id == rating_alias.book_id)
                .where(
                    rating_alias.user_id.in_(select(similar_users_subquery.c.user_id)),
                    rating_alias.rating >= min_rating,
                    ~book_alias.id.in_(select(rated_books_subquery.c.book_id)),
                )
            )

            query = (
                query.group_by(book_alias.id)
                .having(func.count(rating_alias.id) >= min_ratings_count)
                .order_by(func.avg(rating_alias.rating).desc(), func.count(rating_alias.id).desc())
                .limit(limit)
            )

            result = await self.db.execute(query)
            books = result.scalars().all()

            logger.info(f"Найдено {len(books)} книг на основе коллаборативной фильтрации для user_id={user_id}")
            if books:
                logger.debug(f"Рекомендованные книги: {[book.id for book in books]}")
            else:
                logger.warning(
                    f"Коллаборативные рекомендации не найдены для user_id={user_id}. "
                    f"Проверьте оценки от похожих пользователей {similar_users} "
                    f"и min_ratings_count={min_ratings_count}"
                )

            return [BookRecommendation.model_validate(book) for book in books]

        except Exception as e:
            logger.error(
                f"Ошибка при получении коллаборативных рекомендаций для user_id={user_id}: {str(e)}", exc_info=True
            )
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
            content_dict = {book.id: book for book in content_recommendations}
            collaborative_dict = {book.id: book for book in collaborative_recommendations}
            all_books = set(content_dict.keys()) | set(collaborative_dict.keys())
            book_scores = {}
            for book_id in all_books:
                content_score = 1.0 if book_id in content_dict else 0.0
                collaborative_score = 1.0 if book_id in collaborative_dict else 0.0
                final_score = content_score * self.content_weight + collaborative_score * self.collaborative_weight
                book_scores[book_id] = final_score

            sorted_books = sorted(book_scores.items(), key=lambda x: x[1], reverse=True)
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
        """
        try:
            user_preferences = await self._get_user_preferences(user_id)
            ratings_stats_query = text(
                """
                SELECT
                    COUNT(*) as rated_books_count,
                    AVG(rating) as avg_rating
                FROM ratings
                WHERE user_id = :user_id
                """
            )
            total_books_query = text(
                """
                SELECT COUNT(*) as total_books_count
                FROM books
                """
            )

            ratings_result = await self.db.execute(ratings_stats_query, {"user_id": user_id})
            ratings_stats = ratings_result.fetchone()
            total_books_result = await self.db.execute(total_books_query)
            total_books = total_books_result.fetchone()

            authors = sorted(user_preferences.get("authors", {}).items(), key=lambda x: x[1]["weight"], reverse=True)[
                :5
            ]
            categories = sorted(
                user_preferences.get("categories", {}).items(), key=lambda x: x[1]["weight"], reverse=True
            )[:5]
            tags = sorted(user_preferences.get("tags", {}).items(), key=lambda x: x[1]["weight"], reverse=True)[:5]

            rated_books_count = ratings_stats.rated_books_count if ratings_stats else 0
            is_collaborative_ready = rated_books_count >= 5
            is_content_ready = (
                len(user_preferences.get("authors", {})) > 0
                or len(user_preferences.get("categories", {})) > 0
                or len(user_preferences.get("tags", {})) > 0
            )

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
        """
        params = []
        for k in sorted(kwargs.keys()):
            v = kwargs[k]
            if v is not None:
                params.append(f"{k}:{v}")

        key = f"{prefix}:{user_id}"
        if params:
            key += f":{':'.join(params)}"

        return key

    def cache_result(self, key, data, expire_seconds=3600):
        """
        Кэширует результат в Redis.
        """
        if not self.redis_client:
            logger.debug("Redis client not available, skipping cache")
            return

        try:
            json_data = jsonable_encoder(data)
            if isinstance(json_data, list):
                if len(json_data) > 10:
                    logger.warning(f"Truncating cache data from {len(json_data)} to 10 items")
                    json_data = json_data[:10]
                for item in json_data:
                    if isinstance(item, dict):
                        allowed_fields = {"id", "title", "author", "category", "rating", "score"}
                        item = {k: v for k, v in item.items() if k in allowed_fields}

            cached_value = json.dumps(json_data)
            if len(cached_value.encode("utf-8")) > 1024 * 1024:
                logger.warning("Cache data too large, skipping cache")
                return

            self.redis_client.setex(key, expire_seconds, cached_value)
            logger.debug(f"Cached result with key: {key}, expires in {expire_seconds}s")
        except Exception as e:
            logger.error(f"Error caching result: {str(e)}")

    def get_cached_result(self, key):
        """
        Получает результат из кэша.
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
