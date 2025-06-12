from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from models.book import Author, Book, Category, Rating, Tag, favorites, likes
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType
from sqlalchemy import and_, desc, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.logger_config import logger


class RecommendationStrategy(str, Enum):
    """Типы стратегий рекомендаций"""

    HYBRID = "hybrid"
    COLLABORATIVE = "collaborative"
    CONTENT = "content"
    POPULARITY = "popularity"
    AUTHOR = "author"
    CATEGORY = "category"
    TAG = "tag"


class RecommendationService:
    """
    Сервис для гибридной рекомендательной системы, объединяющей:
    - Коллаборативную фильтрацию на основе пользователей
    - Рекомендации на основе контента
    - Рекомендации на основе популярности
    - Рекомендации на основе авторов/категорий/тегов
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.similarity_cache = {}  # Кэш для хранения сходства между пользователями

    async def get_user_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        min_rating: float = 3.0,
        min_ratings_count: int = 5,
        recommendation_type: RecommendationType = RecommendationType.HYBRID,
        cache: bool = True,
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации книг для пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_ratings_count: Минимальное количество оценок
            recommendation_type: Тип рекомендаций
            cache: Использовать ли кэширование
        """
        try:
            # Получаем уже оцененные пользователем книги
            rated_book_ids = await self._get_rated_book_ids(user_id)
            liked_book_ids = await self._get_liked_book_ids(user_id)
            favorited_book_ids = await self._get_favorited_book_ids(user_id)

            # Объединяем все ID книг, которые пользователь уже оценил
            exclude_book_ids = set(rated_book_ids) | set(liked_book_ids) | set(favorited_book_ids)

            # Выбираем метод рекомендаций
            if recommendation_type == RecommendationType.COLLABORATIVE:
                recommendations = await self._get_collaborative_recommendations(
                    user_id, limit, min_rating, min_ratings_count, exclude_book_ids
                )
            elif recommendation_type == RecommendationType.CONTENT:
                recommendations = await self._get_content_based_recommendations(
                    user_id, limit, min_rating, min_ratings_count, exclude_book_ids
                )
            elif recommendation_type == RecommendationType.POPULARITY:
                recommendations = await self._get_popularity_recommendations(
                    limit, min_rating, min_ratings_count, exclude_book_ids
                )
            elif recommendation_type == RecommendationType.AUTHOR:
                recommendations = await self._get_author_based_recommendations(
                    user_id, limit, min_rating, min_ratings_count, exclude_book_ids
                )
            elif recommendation_type == RecommendationType.CATEGORY:
                recommendations = await self._get_category_based_recommendations(
                    user_id, limit, min_rating, min_ratings_count, exclude_book_ids
                )
            elif recommendation_type == RecommendationType.TAG:
                recommendations = await self._get_tag_based_recommendations(
                    user_id, limit, min_rating, min_ratings_count, exclude_book_ids
                )
            else:  # HYBRID
                recommendations = await self.get_hybrid_recommendations(user_id, limit, exclude_book_ids)

            # Сортируем рекомендации по убыванию оценки
            recommendations.sort(key=lambda x: x.score, reverse=True)
            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Error in get_user_recommendations: {str(e)}")
            return []

    async def _get_rated_book_ids(self, user_id: int) -> List[int]:
        """
        Получить ID книг, которые пользователь уже оценил.

        Args:
            user_id: ID пользователя
        """
        query = select(Rating.book_id).where(Rating.user_id == user_id)
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def _get_liked_book_ids(self, user_id: int) -> List[int]:
        """
        Получить ID книг, которые пользователь лайкнул.

        Args:
            user_id: ID пользователя
        """
        query = select(likes.c.book_id).where(likes.c.user_id == user_id)
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def _get_favorited_book_ids(self, user_id: int) -> List[int]:
        """
        Получить ID книг, которые пользователь добавил в избранное.

        Args:
            user_id: ID пользователя
        """
        query = select(favorites.c.book_id).where(favorites.c.user_id == user_id)
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def _get_user_ratings(self, user_id: int) -> Dict[int, float]:
        """Получить словарь {book_id: rating} для оценок пользователя"""
        query = select(Rating.book_id, Rating.rating).where(Rating.user_id == user_id)
        result = await self.db.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def _get_all_users_with_ratings(self) -> List[int]:
        """
        Получить список ID пользователей, у которых есть оценки.
        """
        query = select(distinct(Rating.user_id))
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def _get_user_interests(self, user_id: int) -> Tuple[Dict[int, float], Dict[int, float], Dict[int, float]]:
        """
        Получить интересы пользователя по авторам, категориям и тегам.

        Args:
            user_id: ID пользователя

        Returns:
            Кортеж из трех словарей:
            - {author_id: вес}
            - {category_id: вес}
            - {tag_id: вес}
        """
        # Получаем оценки пользователя
        user_ratings = await self._get_user_ratings(user_id)
        book_ids = list(user_ratings.keys())

        if not book_ids:
            return {}, {}, {}

        # Получаем информацию о книгах
        query = (
            select(Book)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .where(Book.id.in_(book_ids))
        )
        result = await self.db.execute(query)
        books = result.scalars().all()

        # Подсчитываем веса авторов, категорий и тегов
        author_weights = {}
        category_weights = {}
        tag_weights = {}

        for book in books:
            rating = user_ratings.get(book.id, 0)
            # Нормализуем рейтинг от 0 до 1
            normalized_rating = (rating - 1) / 4  # от 1-5 до 0-1

            if book.author_id:
                author_weights[book.author_id] = author_weights.get(book.author_id, 0) + normalized_rating

            if book.category_id:
                category_weights[book.category_id] = category_weights.get(book.category_id, 0) + normalized_rating

            for tag in book.tags:
                tag_weights[tag.id] = tag_weights.get(tag.id, 0) + normalized_rating

        # Нормализуем веса
        author_sum = sum(author_weights.values()) or 1
        category_sum = sum(category_weights.values()) or 1
        tag_sum = sum(tag_weights.values()) or 1

        author_weights = {k: v / author_sum for k, v in author_weights.items()}
        category_weights = {k: v / category_sum for k, v in category_weights.items()}
        tag_weights = {k: v / tag_sum for k, v in tag_weights.items()}

        return author_weights, category_weights, tag_weights

    async def _get_similar_users(self, user_id: int, min_common_ratings: int = 3) -> List[Dict[str, Any]]:
        """
        Найти пользователей, похожих на указанного пользователя.

        Args:
            user_id: ID пользователя
            min_common_ratings: Минимальное количество общих оценок

        Returns:
            Список словарей с id и оценкой похожести пользователей
        """
        try:
            user_ratings = await self._get_user_ratings(user_id)
            if not user_ratings:
                return []

            query = select(distinct(Rating.user_id))
            result = await self.db.execute(query)
            all_users = [row[0] for row in result.all()]

            similar_users = []
            for other_user_id in all_users:
                if other_user_id == user_id:
                    continue

                other_user_ratings = await self._get_user_ratings(other_user_id)
                common_books = set(user_ratings.keys()) & set(other_user_ratings.keys())

                if len(common_books) >= min_common_ratings:
                    user_vector = [user_ratings[book_id] for book_id in common_books]
                    other_vector = [other_user_ratings[book_id] for book_id in common_books]
                    similarity = self._calculate_cosine_similarity(user_vector, other_vector)

                    if similarity > 0:
                        similar_users.append({"user_id": other_user_id, "similarity": similarity})

            similar_users.sort(key=lambda user: user["similarity"], reverse=True)
            return similar_users

        except Exception as e:
            logger.error(f"Error in _get_similar_users: {str(e)}")
            return []

    async def _get_book_recommendation_object(self, book: Book, score: float, reason: str) -> BookRecommendation:
        """
        Создать объект рекомендации книги.

        Args:
            book: Объект книги
            score: Оценка рекомендации
            reason: Причина рекомендации
        """
        author_names = [author.name for author in book.authors]
        category_name = book.categories[0].name_categories if book.categories else None
        avg_rating = book.ratings[0].rating if book.ratings else None

        return BookRecommendation(
            id=book.id,
            book_id=book.id,
            title=book.title,
            author_names=author_names,
            category=category_name,
            year=book.year,
            cover=book.cover,
            rating=avg_rating,
            score=score,
            reason=reason,
            recommendation_type=RecommendationType.CONTENT,
        )

    async def _get_collaborative_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        min_rating: float = 2.5,
        min_ratings_count: int = 3,
        exclude_book_ids: Set[int] = None,
    ) -> List[BookRecommendation]:
        """
        Получить коллаборативные рекомендации на основе оценок похожих пользователей.
        """
        try:
            # Получаем оценки текущего пользователя
            user_ratings_query = select(Rating.book_id, Rating.rating).where(Rating.user_id == user_id)
            result = await self.db.execute(user_ratings_query)
            user_ratings = {row[0]: row[1] for row in result.all()}

            if not user_ratings:
                return []

            # Получаем всех пользователей, которые оценили хотя бы одну книгу
            users_query = select(distinct(Rating.user_id))
            result = await self.db.execute(users_query)
            all_users = [row[0] for row in result.all()]

            # Находим похожих пользователей
            similar_users = []
            for other_user_id in all_users:
                if other_user_id == user_id:
                    continue

                # Получаем оценки другого пользователя
                other_ratings_query = select(Rating.book_id, Rating.rating).where(Rating.user_id == other_user_id)
                result = await self.db.execute(other_ratings_query)
                other_ratings = {row[0]: row[1] for row in result.all()}

                # Находим общие книги
                common_books = set(user_ratings.keys()) & set(other_ratings.keys())
                if len(common_books) >= 3:  # Минимум 3 общие книги
                    user_vector = [user_ratings[book_id] for book_id in common_books]
                    other_vector = [other_ratings[book_id] for book_id in common_books]
                    similarity = self._calculate_cosine_similarity(user_vector, other_vector)

                    if similarity > 0:
                        similar_users.append(
                            {"user_id": other_user_id, "similarity": similarity, "ratings": other_ratings}
                        )

            if not similar_users:
                return []

            # Сортируем похожих пользователей по схожести
            similar_users.sort(key=lambda x: x["similarity"], reverse=True)
            top_similar_users = similar_users[:5]  # Берем топ-5 похожих пользователей

            # Собираем книги, которые оценили похожие пользователи
            similar_user_ids = [user["user_id"] for user in top_similar_users]
            similar_books_query = (
                select(Book)
                .options(joinedload(Book.authors), joinedload(Book.categories), selectinload(Book.tags))
                .join(Rating, Book.id == Rating.book_id)
                .where(and_(Rating.user_id.in_(similar_user_ids), Rating.rating >= min_rating))
            )

            if exclude_book_ids:
                similar_books_query = similar_books_query.where(Book.id.notin_(list(exclude_book_ids)))

            similar_books_query = (
                similar_books_query.group_by(Book.id)
                .having(func.count(Rating.id) >= min_ratings_count)
                .order_by(desc(func.avg(Rating.rating)))
                .limit(limit * 2)
            )

            result = await self.db.execute(similar_books_query)
            similar_books = result.unique().scalars().all()

            recommendations = []
            for book in similar_books:
                try:
                    # Вычисляем взвешенный рейтинг на основе схожести пользователей
                    weighted_rating = 0
                    total_similarity = 0

                    for similar_user in top_similar_users:
                        if book.id in similar_user["ratings"]:
                            weighted_rating += similar_user["similarity"] * similar_user["ratings"][book.id]
                            total_similarity += similar_user["similarity"]

                    if total_similarity > 0:
                        avg_rating = weighted_rating / total_similarity
                    else:
                        avg_rating = await self._get_book_avg_rating(book.id)

                    # Формируем список похожих пользователей, которые оценили эту книгу
                    similar_users_who_rated = [
                        user
                        for user in top_similar_users
                        if book.id in user["ratings"] and user["ratings"][book.id] >= 4
                    ]

                    reason = "Рекомендуется на основе оценок похожих пользователей"
                    if similar_users_who_rated:
                        reason = f"Рекомендуется {len(similar_users_who_rated)} похожими пользователями"

                    recommendation = BookRecommendation(
                        id=book.id,
                        book_id=book.id,
                        title=book.title,
                        author_names=[author.name for author in book.authors] if book.authors else [],
                        category=book.categories[0].name_categories if book.categories else None,
                        year=book.year,
                        cover=book.cover,
                        rating=avg_rating,
                        score=avg_rating,
                        reason=reason,
                        recommendation_type=RecommendationType.COLLABORATIVE,
                    )
                    recommendations.append(recommendation)
                except Exception as e:
                    logger.error(f"Error processing book {book.id}: {str(e)}")
                    continue

            # Сортируем рекомендации по рейтингу
            recommendations.sort(key=lambda x: x.score, reverse=True)
            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Error in _get_collaborative_recommendations: {str(e)}")
            return []

    async def _get_content_based_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        min_rating: float = 2.5,
        min_ratings_count: int = 3,
        exclude_book_ids: Set[int] = None,
    ) -> List[BookRecommendation]:
        """
        Получить контентные рекомендации на основе предпочтений пользователя.
        """
        try:
            logger.info(f"Starting content-based recommendations for user {user_id}")

            # Получаем все оценки пользователя
            ratings_query = select(Rating.book_id, Rating.rating).where(Rating.user_id == user_id)
            result = await self.db.execute(ratings_query)
            user_ratings = {row[0]: row[1] for row in result.all()}

            logger.info(f"User {user_id} has {len(user_ratings)} ratings")

            # Получаем книги, которые пользователь оценил
            rated_book_ids = list(user_ratings.keys())

            if not rated_book_ids:
                logger.info(f"No rated books found for user {user_id}")
                return []

            # Получаем информацию о книгах
            books_query = (
                select(Book)
                .options(joinedload(Book.authors), joinedload(Book.categories), selectinload(Book.tags))
                .where(Book.id.in_(rated_book_ids))
            )
            result = await self.db.execute(books_query)
            user_rated_books = result.unique().scalars().all()

            logger.info(f"Found {len(user_rated_books)} rated books with details")

            # Собираем ID авторов и категорий
            author_ids = set()
            category_ids = set()

            for book in user_rated_books:
                author_ids.update(author.id for author in book.authors)
                category_ids.update(category.id for category in book.categories)

            logger.info(f"Found {len(author_ids)} authors, {len(category_ids)} categories")

            if not author_ids and not category_ids:
                logger.info("No authors or categories found")
                return []

            # Ищем книги тех же авторов или категорий
            similar_books_query = (
                select(Book)
                .options(joinedload(Book.authors), joinedload(Book.categories), selectinload(Book.tags))
                .where(
                    or_(Book.authors.any(Author.id.in_(author_ids)), Book.categories.any(Category.id.in_(category_ids)))
                )
            )

            if exclude_book_ids:
                similar_books_query = similar_books_query.where(Book.id.notin_(list(exclude_book_ids)))

            similar_books_query = similar_books_query.limit(limit * 2)

            result = await self.db.execute(similar_books_query)
            similar_books = result.unique().scalars().all()

            logger.info(f"Found {len(similar_books)} similar books")

            recommendations = []
            for book in similar_books:
                try:
                    # Получаем средний рейтинг книги
                    avg_rating_query = select(func.avg(Rating.rating)).where(Rating.book_id == book.id)
                    avg_rating_result = await self.db.execute(avg_rating_query)
                    avg_rating = avg_rating_result.scalar() or 0.0

                    # Определяем причину рекомендации
                    reason_parts = []
                    if any(author.id in author_ids for author in book.authors):
                        author_names = [author.name for author in book.authors if author.id in author_ids]
                        reason_parts.append(f"от автора {', '.join(author_names)}")
                    if any(category.id in category_ids for category in book.categories):
                        category_names = [
                            category.name_categories for category in book.categories if category.id in category_ids
                        ]
                        reason_parts.append(f"в категории {', '.join(category_names)}")

                    reason = "Рекомендуется на основе ваших предпочтений"
                    if reason_parts:
                        reason = "Рекомендуется " + ", ".join(reason_parts)

                    recommendation = BookRecommendation(
                        id=book.id,
                        book_id=book.id,
                        title=book.title,
                        author_names=[author.name for author in book.authors] if book.authors else [],
                        category=book.categories[0].name_categories if book.categories else None,
                        year=book.year,
                        cover=book.cover,
                        rating=avg_rating,
                        score=avg_rating,
                        reason=reason,
                        recommendation_type=RecommendationType.CONTENT,
                    )
                    recommendations.append(recommendation)
                except Exception as e:
                    logger.error(f"Error processing book {book.id}: {str(e)}")
                    continue

            # Сортируем рекомендации по рейтингу
            recommendations.sort(key=lambda x: x.score, reverse=True)
            logger.info(f"Returning {len(recommendations)} recommendations")
            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Error in _get_content_based_recommendations: {str(e)}")
            return []

    async def get_hybrid_recommendations(
        self, user_id: int, limit: int = 15, exclude_book_ids: Set[int] = None
    ) -> List[BookRecommendation]:
        """
        Получить гибридные рекомендации, комбинирующие коллаборативную и контентную фильтрацию.
        """
        try:
            logger.info(f"Starting hybrid recommendations for user {user_id}")

            # Сначала пробуем получить контентные рекомендации
            content = await self._get_content_based_recommendations(user_id, limit * 2, 2.5, 3, exclude_book_ids)
            logger.info(f"Got {len(content)} content-based recommendations")

            if content:
                # Если есть контентные рекомендации, возвращаем их
                return content[:limit]

            # Если контентных рекомендаций нет, пробуем коллаборативные
            collaborative = await self._get_collaborative_recommendations(user_id, limit * 2, 2.5, 3, exclude_book_ids)
            logger.info(f"Got {len(collaborative)} collaborative recommendations")

            if collaborative:
                return collaborative[:limit]

            # Если нет ни контентных, ни коллаборативных, возвращаем популярные
            popularity = await self._get_popularity_recommendations(limit, 2.0, 2, exclude_book_ids)
            logger.info(f"Got {len(popularity)} popularity recommendations")

            return popularity[:limit]

        except Exception as e:
            logger.error(f"Error in get_hybrid_recommendations: {str(e)}")
            return []

    async def _get_popularity_recommendations(
        self, limit: int = 10, min_rating: float = 2.5, min_ratings_count: int = 3, exclude_book_ids: Set[int] = None
    ) -> List[BookRecommendation]:
        """
        Получить рекомендации на основе популярности книг.
        """
        try:
            # Формируем базовый запрос
            query = (
                select(Book)
                .options(joinedload(Book.authors), joinedload(Book.categories), selectinload(Book.tags))
                .join(Rating, Book.id == Rating.book_id)
                .where(Rating.rating >= min_rating)
            )

            # Добавляем условие исключения книг, если они указаны
            if exclude_book_ids and len(exclude_book_ids) > 0:
                query = query.where(Book.id.notin_(list(exclude_book_ids)))

            # Добавляем подсчет оценок и средний рейтинг
            query = (
                query.group_by(Book.id)
                .having(func.count(Rating.id) >= min_ratings_count)
                .order_by(desc(func.avg(Rating.rating)))
                .limit(limit)
            )

            result = await self.db.execute(query)
            books = result.scalars().all()

            recommendations = []
            for book in books:
                try:
                    # Получаем средний рейтинг книги
                    avg_rating = await self._get_book_avg_rating(book.id)

                    # Создаем объект рекомендации
                    recommendation = BookRecommendation(
                        id=book.id,
                        book_id=book.id,
                        title=book.title,
                        author_names=[author.name for author in book.authors] if book.authors else [],
                        category=book.categories[0].name_categories if book.categories else None,
                        year=book.year,
                        cover=book.cover,
                        rating=avg_rating,
                        score=avg_rating,
                        reason="Популярная книга с высоким рейтингом",
                        recommendation_type=RecommendationType.POPULARITY,
                    )
                    recommendations.append(recommendation)
                except Exception as e:
                    logger.error(f"Error processing book {book.id}: {str(e)}")
                    continue

            return recommendations

        except Exception as e:
            logger.error(f"Error in _get_popularity_recommendations: {str(e)}")
            return []

    async def get_recommendation_stats(self, user_id: int) -> RecommendationStats:
        """
        Получает статистику для рекомендаций пользователя.

        Args:
            user_id: ID пользователя
        """
        # Получаем рейтинги пользователя
        user_ratings = await self._get_user_ratings(user_id)

        # Получаем количество оцененных книг
        rated_books_count = len(user_ratings)

        # Получаем любимых авторов, категории и теги
        favorite_authors = await self._get_user_favorite_authors(user_id)
        favorite_categories = await self._get_user_favorite_categories(user_id)
        favorite_tags = await self._get_user_favorite_tags(user_id)

        # Получаем общее количество книг
        query = select(func.count(Book.id))
        result = await self.db.execute(query)
        total_books_count = result.scalar() or 0

        # Получаем имена авторов
        authors = []
        if favorite_authors:
            query = select(Author).where(Author.id.in_(favorite_authors))
            result = await self.db.execute(query)
            authors = [author.name for author in result.scalars().all()]

        # Получаем названия категорий
        categories = []
        if favorite_categories:
            query = select(Category).where(Category.id.in_(favorite_categories))
            result = await self.db.execute(query)
            categories = [category.name_categories for category in result.scalars().all()]

        # Получаем названия тегов
        tags = []
        if favorite_tags:
            query = select(Tag).where(Tag.id.in_(favorite_tags))
            result = await self.db.execute(query)
            tags = [tag.name_tag for tag in result.scalars().all()]

        # Вычисляем средний рейтинг пользователя
        if user_ratings:
            avg_rating = sum(user_ratings.values()) / len(user_ratings)
        else:
            avg_rating = 0.0

        # Достаточно ли данных для рекомендаций разных типов
        is_collaborative_ready = rated_books_count >= 5
        is_content_ready = bool(favorite_authors or favorite_categories or favorite_tags)

        # Возвращаем статистику
        return RecommendationStats(
            user_id=user_id,
            rated_books_count=rated_books_count,
            total_books_count=total_books_count,
            avg_rating=avg_rating,
            favorite_authors=authors,
            favorite_categories=categories,
            favorite_tags=tags,
            is_collaborative_ready=is_collaborative_ready,
            is_content_ready=is_content_ready,
        )

    async def _get_user_favorite_authors(self, user_id: int) -> List[int]:
        """Получить ID авторов, книги которых пользователь оценил высоко (>=4)"""
        try:
            query = (
                select(Author.id)
                .join(Book.authors)
                .join(Rating, Rating.book_id == Book.id)
                .where(Rating.user_id == user_id, Rating.rating >= 4)
                .group_by(Author.id)
                .having(func.count(Book.id) >= 1)
            )
            result = await self.db.execute(query)
            return [row[0] for row in result.all()]
        except Exception as e:
            logger.error(f"Error in _get_user_favorite_authors: {str(e)}")
            return []

    async def _get_user_favorite_categories(self, user_id: int) -> List[int]:
        """Получить ID категорий, книги которых пользователь оценил высоко (>=4)"""
        try:
            query = (
                select(Category.id)
                .join(Book.categories)
                .join(Rating, Rating.book_id == Book.id)
                .where(Rating.user_id == user_id, Rating.rating >= 4)
                .group_by(Category.id)
                .having(func.count(Book.id) >= 1)
            )
            result = await self.db.execute(query)
            return [row[0] for row in result.all()]
        except Exception as e:
            logger.error(f"Error in _get_user_favorite_categories: {str(e)}")
            return []

    async def _get_user_favorite_tags(self, user_id: int) -> List[int]:
        """Получить ID тегов, книги которых пользователь оценил высоко (>=4)"""
        # Здесь предполагается наличие связи многие-ко-многим книг и тегов через таблицу book_tags
        # Если структура отличается, необходимо адаптировать запрос
        query = (
            select(Tag.id)
            .join(Book.tags)
            .join(Rating, Rating.book_id == Book.id)
            .where(Rating.user_id == user_id, Rating.rating >= 4)
            .group_by(Tag.id)
            .having(func.count(Book.id) >= 1)
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def _get_book_detail(self, book_id: int) -> Optional[Book]:
        """Получить детали книги по ID"""
        query = (
            select(Book)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .where(Book.id == book_id)
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def _get_book_avg_rating(self, book_id: int) -> float:
        """Получить средний рейтинг книги"""
        query = select(func.avg(Rating.rating)).where(Rating.book_id == book_id)
        result = await self.db.execute(query)
        rating = result.scalar()
        return rating if rating is not None else 0.0

    async def _get_author_based_recommendations(
        self,
        user_id: int,
        limit: int,
        min_rating: float,
        min_ratings_count: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        """
        Получает рекомендации на основе любимых авторов пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_ratings_count: Минимальное количество оценок
            exclude_book_ids: ID книг, которые следует исключить из рекомендаций
        """
        # Получаем любимых авторов пользователя
        favorite_authors = await self._get_user_favorite_authors(user_id)
        if not favorite_authors:
            return []

        # Создаем подзапрос для рейтингов
        ratings_subquery = (
            select(
                Rating.book_id,
                func.avg(Rating.rating).label("avg_rating"),
                func.count(Rating.id).label("ratings_count"),
            )
            .group_by(Rating.book_id)
            .having(func.avg(Rating.rating) >= min_rating, func.count(Rating.id) >= min_ratings_count)
            .subquery()
        )

        # Основной запрос для получения книг любимых авторов
        query = (
            select(Book, ratings_subquery.c.avg_rating, ratings_subquery.c.ratings_count)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .join(ratings_subquery, Book.id == ratings_subquery.c.book_id)
            .where(Book.author_id.in_(favorite_authors))
        )

        # Исключаем книги, которые пользователь уже взаимодействовал
        if exclude_book_ids:
            query = query.where(Book.id.notin_(exclude_book_ids))

        # Сортируем по среднему рейтингу (лучшие сначала)
        query = query.order_by(desc(ratings_subquery.c.avg_rating))

        # Ограничиваем количество результатов
        query = query.limit(limit)

        # Выполняем запрос
        result = await self.db.execute(query)
        rows = result.all()

        # Создаем рекомендации
        recommendations = []
        for row in rows:
            book, avg_rating, ratings_count = row

            # Нормализуем оценку (от 0 до 1)
            normalized_score = min(avg_rating / 5.0, 1.0)

            # Создаем рекомендацию
            author_name = book.author.name if book.author else "Неизвестный автор"
            category_name = book.category.name_categories if book.category else "Без категории"

            recommendations.append(
                BookRecommendation(
                    id=book.id,
                    title=book.title,
                    author=author_name,
                    category=category_name,
                    rating=avg_rating,
                    year=book.publication_year,
                    score=normalized_score,
                    recommendation_type=RecommendationType.AUTHOR,
                )
            )

        return recommendations

    async def _get_category_based_recommendations(
        self,
        user_id: int,
        limit: int,
        min_rating: float,
        min_ratings_count: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        """
        Получает рекомендации на основе любимых категорий пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_ratings_count: Минимальное количество оценок
            exclude_book_ids: ID книг, которые следует исключить из рекомендаций
        """
        # Получаем любимые категории пользователя
        favorite_categories = await self._get_user_favorite_categories(user_id)
        if not favorite_categories:
            return []

        # Создаем подзапрос для рейтингов
        ratings_subquery = (
            select(
                Rating.book_id,
                func.avg(Rating.rating).label("avg_rating"),
                func.count(Rating.id).label("ratings_count"),
            )
            .group_by(Rating.book_id)
            .having(func.avg(Rating.rating) >= min_rating, func.count(Rating.id) >= min_ratings_count)
            .subquery()
        )

        # Основной запрос для получения книг любимых категорий
        query = (
            select(Book, ratings_subquery.c.avg_rating, ratings_subquery.c.ratings_count)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .join(ratings_subquery, Book.id == ratings_subquery.c.book_id)
            .where(Book.category_id.in_(favorite_categories))
        )

        # Исключаем книги, которые пользователь уже взаимодействовал
        if exclude_book_ids:
            query = query.where(Book.id.notin_(exclude_book_ids))

        # Сортируем по среднему рейтингу (лучшие сначала)
        query = query.order_by(desc(ratings_subquery.c.avg_rating))

        # Ограничиваем количество результатов
        query = query.limit(limit)

        # Выполняем запрос
        result = await self.db.execute(query)
        rows = result.all()

        # Создаем рекомендации
        recommendations = []
        for row in rows:
            book, avg_rating, ratings_count = row

            # Нормализуем оценку (от 0 до 1)
            normalized_score = min(avg_rating / 5.0, 1.0)

            # Создаем рекомендацию
            author_name = book.author.name if book.author else "Неизвестный автор"
            category_name = book.category.name_categories if book.category else "Без категории"

            recommendations.append(
                BookRecommendation(
                    id=book.id,
                    title=book.title,
                    author=author_name,
                    category=category_name,
                    rating=avg_rating,
                    year=book.publication_year,
                    score=normalized_score,
                    recommendation_type=RecommendationType.CATEGORY,
                )
            )

        return recommendations

    async def _get_tag_based_recommendations(
        self,
        user_id: int,
        limit: int,
        min_rating: float,
        min_ratings_count: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        """
        Получает рекомендации на основе любимых тегов пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_ratings_count: Минимальное количество оценок
            exclude_book_ids: ID книг, которые следует исключить из рекомендаций
        """
        # Получаем любимые теги пользователя
        favorite_tags = await self._get_user_favorite_tags(user_id)
        if not favorite_tags:
            return []

        # Создаем подзапрос для рейтингов
        ratings_subquery = (
            select(
                Rating.book_id,
                func.avg(Rating.rating).label("avg_rating"),
                func.count(Rating.id).label("ratings_count"),
            )
            .group_by(Rating.book_id)
            .having(func.avg(Rating.rating) >= min_rating, func.count(Rating.id) >= min_ratings_count)
            .subquery()
        )

        # Основной запрос для получения книг с любимыми тегами
        query = (
            select(Book, ratings_subquery.c.avg_rating, ratings_subquery.c.ratings_count)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .join(ratings_subquery, Book.id == ratings_subquery.c.book_id)
            .where(Book.tags.any(Tag.id.in_(favorite_tags)))
        )

        # Исключаем книги, которые пользователь уже взаимодействовал
        if exclude_book_ids:
            query = query.where(Book.id.notin_(exclude_book_ids))

        # Сортируем по среднему рейтингу (лучшие сначала)
        query = query.order_by(desc(ratings_subquery.c.avg_rating))

        # Ограничиваем количество результатов
        query = query.limit(limit)

        # Выполняем запрос
        result = await self.db.execute(query)
        rows = result.all()

        # Создаем рекомендации
        recommendations = []
        for row in rows:
            book, avg_rating, ratings_count = row

            # Нормализуем оценку (от 0 до 1)
            normalized_score = min(avg_rating / 5.0, 1.0)

            # Создаем рекомендацию
            author_name = book.author.name if book.author else "Неизвестный автор"
            category_name = book.category.name_categories if book.category else "Без категории"

            recommendations.append(
                BookRecommendation(
                    id=book.id,
                    title=book.title,
                    author=author_name,
                    category=category_name,
                    rating=avg_rating,
                    year=book.publication_year,
                    score=normalized_score,
                    recommendation_type=RecommendationType.TAG,
                )
            )

        return recommendations

    async def get_content_based_recommendations(
        self, user_id: int, limit: int = 10, exclude_book_ids: List[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить рекомендации на основе содержания (авторы, категории, теги).

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            exclude_book_ids: Список ID книг, которые нужно исключить

        Returns:
            Список рекомендованных книг с рейтингами и причинами
        """
        author_weights, category_weights, tag_weights = await self._get_user_interests(user_id)

        if not author_weights and not category_weights and not tag_weights:
            return []

        # Исключаем книги, которые пользователь уже оценил или указал в exclude_book_ids
        exclude_ids = await self._get_exclude_book_ids(user_id, exclude_book_ids)

        # Получаем все книги
        query = (
            select(Book)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .where(Book.id.notin_(exclude_ids if exclude_ids else [0]))
            .limit(100)  # Ограничиваем количество книг для обработки
        )
        result = await self.db.execute(query)
        books = result.scalars().all()

        # Ранжируем книги по схожести с интересами пользователя
        recommendations = []
        for book in books:
            # Вычисляем общий счет на основе авторов, категорий и тегов
            author_score = author_weights.get(book.author_id, 0) if book.author_id else 0
            category_score = category_weights.get(book.category_id, 0) if book.category_id else 0

            tag_score = 0
            for tag in book.tags:
                tag_score += tag_weights.get(tag.id, 0)

            # Нормализуем оценку тегов
            tag_score = tag_score / len(book.tags) if book.tags else 0

            # Вычисляем общую оценку
            content_score = (author_score * 0.4 + category_score * 0.3 + tag_score * 0.3) * 0.7
            popularity_score = (book.average_rating or 0) / 5 * 0.3
            total_score = content_score + popularity_score

            # Определяем причину рекомендации
            reason_parts = []
            if author_score > 0 and book.author:
                reason_parts.append(f"от автора {book.author.name}")
            if category_score > 0 and book.category:
                reason_parts.append(f"в категории {book.category.name_categories}")
            if tag_score > 0 and book.tags:
                top_tag = max(book.tags, key=lambda tag: tag_weights.get(tag.id, 0), default=None)
                if top_tag:
                    reason_parts.append(f"с тегом {top_tag.name_tag}")

            reason = "Похоже на книги, которые вам нравятся"
            if reason_parts:
                reason = "Похоже на книги, которые вам нравятся: " + ", ".join(reason_parts)

            recommendations.append(
                {
                    "book": {
                        "id": book.id,
                        "title": book.title,
                        "author": book.author.name if book.author else None,
                        "category": book.category.name_categories if book.category else None,
                        "tags": [tag.name_tag for tag in book.tags],
                        "average_rating": book.average_rating,
                        "ratings_count": book.ratings_count,
                        "cover_image": book.cover_image,
                    },
                    "score": total_score,
                    "reason": reason,
                    "strategy": RecommendationStrategy.CONTENT,
                }
            )

        # Сортируем по оценке и ограничиваем количество
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:limit]

    async def get_recommendations_by_category(
        self, user_id: int, limit: int = 10, exclude_book_ids: List[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить рекомендации книг по категориям, которые пользователь оценил положительно.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            exclude_book_ids: Список ID книг, которые нужно исключить

        Returns:
            Список рекомендованных книг с рейтингами и причинами
        """
        _, category_weights, _ = await self._get_user_interests(user_id)

        if not category_weights:
            return []

        # Исключаем книги, которые пользователь уже оценил или указал в exclude_book_ids
        exclude_ids = await self._get_exclude_book_ids(user_id, exclude_book_ids)

        # Получаем лучшие категории
        top_categories = sorted(category_weights.items(), key=lambda x: x[1], reverse=True)[:5]
        top_category_ids = [category_id for category_id, _ in top_categories]

        # Получаем книги из этих категорий
        query = (
            select(Book)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .where(Book.category_id.in_(top_category_ids), Book.id.notin_(exclude_ids if exclude_ids else [0]))
            .order_by(Book.average_rating.desc())
            .limit(limit * 2)
        )
        result = await self.db.execute(query)
        books = result.scalars().all()

        # Ранжируем книги по весу категории и рейтингу
        recommendations = []
        for book in books:
            category_weight = category_weights.get(book.category_id, 0)

            score = category_weight * 0.7 + (book.average_rating or 0) / 5 * 0.3

            recommendations.append(
                {
                    "book": {
                        "id": book.id,
                        "title": book.title,
                        "author": book.author.name if book.author else None,
                        "category": book.category.name_categories if book.category else None,
                        "tags": [tag.name_tag for tag in book.tags],
                        "average_rating": book.average_rating,
                        "ratings_count": book.ratings_count,
                        "cover_image": book.cover_image,
                    },
                    "score": score,
                    "reason": f"В категории {book.category.name_categories if book.category else 'Без категории'}, которую вы оценили высоко",
                    "strategy": RecommendationStrategy.CATEGORY,
                }
            )

        # Сортируем по оценке и ограничиваем количество
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:limit]

    async def get_recommendations_by_tag(
        self, user_id: int, limit: int = 10, exclude_book_ids: List[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить рекомендации книг по тегам, которые пользователь оценил положительно.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            exclude_book_ids: Список ID книг, которые нужно исключить

        Returns:
            Список рекомендованных книг с рейтингами и причинами
        """
        _, _, tag_weights = await self._get_user_interests(user_id)

        if not tag_weights:
            return []

        # Исключаем книги, которые пользователь уже оценил или указал в exclude_book_ids
        exclude_ids = await self._get_exclude_book_ids(user_id, exclude_book_ids)

        # Получаем лучшие теги
        top_tags = sorted(tag_weights.items(), key=lambda x: x[1], reverse=True)[:5]
        top_tag_ids = [tag_id for tag_id, _ in top_tags]

        # Получаем книги с этими тегами
        query = (
            select(Book)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .join(Book.tags)
            .where(and_(Tag.id.in_(top_tag_ids), Book.id.notin_(exclude_ids) if exclude_ids else True))
            .order_by(Book.average_rating.desc())
            .limit(limit * 2)
        )
        result = await self.db.execute(query)
        books = result.scalars().all()

        # Ранжируем книги по весу тега и рейтингу
        recommendations = []
        for book in books:
            book_tag_ids = [tag.id for tag in book.tags]

            # Высчитываем суммарный вес тегов для книги
            tag_sum = sum(tag_weights.get(tag_id, 0) for tag_id in book_tag_ids)
            avg_tag_weight = tag_sum / len(book_tag_ids) if book_tag_ids else 0

            score = avg_tag_weight * 0.7 + (book.average_rating or 0) / 5 * 0.3

            # Находим тег с наивысшим весом
            top_tag_for_book = None
            top_tag_weight = 0
            for tag in book.tags:
                weight = tag_weights.get(tag.id, 0)
                if weight > top_tag_weight:
                    top_tag_weight = weight
                    top_tag_for_book = tag

            recommendations.append(
                {
                    "book": {
                        "id": book.id,
                        "title": book.title,
                        "author": book.author.name if book.author else None,
                        "category": book.category.name_categories if book.category else None,
                        "tags": [tag.name_tag for tag in book.tags],
                        "average_rating": book.average_rating,
                        "ratings_count": book.ratings_count,
                        "cover_image": book.cover_image,
                    },
                    "score": score,
                    "reason": f"С тегом {top_tag_for_book.name_tag if top_tag_for_book else 'популярным'}, который вам интересен",
                    "strategy": RecommendationStrategy.TAG,
                }
            )

        # Сортируем по оценке и ограничиваем количество
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:limit]

    async def _get_exclude_book_ids(self, user_id: int, exclude_book_ids: List[int] = None) -> List[int]:
        """
        Получить список ID книг, которые нужно исключить из рекомендаций.
        Это книги, которые пользователь уже оценил или которые явно исключены.

        Args:
            user_id: ID пользователя
            exclude_book_ids: Дополнительный список ID книг для исключения

        Returns:
            Объединенный список ID книг для исключения
        """
        # Получаем ID книг, которые пользователь уже оценил
        rated_books = await self._get_rated_book_ids(user_id)

        # Получаем ID книг, которые пользователь лайкнул
        liked_books = await self._get_liked_book_ids(user_id)

        # Получаем ID книг, которые пользователь добавил в избранное
        favorited_books = await self._get_favorited_book_ids(user_id)

        # Объединяем все списки
        result = list(set(rated_books + liked_books + favorited_books))

        # Добавляем явно исключенные книги
        if exclude_book_ids:
            result.extend([book_id for book_id in exclude_book_ids if book_id not in result])

        return result

    def _calculate_cosine_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """
        Вычислить косинусное сходство между двумя векторами.

        Args:
            vector1: Первый вектор
            vector2: Второй вектор

        Returns:
            Косинусное сходство (от 0 до 1)
        """
        if not vector1 or not vector2 or len(vector1) != len(vector2):
            return 0

        # Вычисляем скалярное произведение
        dot_product = sum(a * b for a, b in zip(vector1, vector2))

        # Вычисляем нормы векторов
        norm1 = sum(a * a for a in vector1) ** 0.5
        norm2 = sum(b * b for b in vector2) ** 0.5

        # Избегаем деления на ноль
        if norm1 == 0 or norm2 == 0:
            return 0

        # Косинусное сходство
        return dot_product / (norm1 * norm2)

    async def _get_user_preferences(self, user_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить предпочтения пользователя по авторам, категориям и тегам.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь с предпочтениями пользователя
        """
        try:
            # Получаем любимых авторов
            favorite_authors = await self._get_user_favorite_authors(user_id)
            authors = []
            if favorite_authors:
                query = select(Author).where(Author.id.in_(favorite_authors))
                result = await self.db.execute(query)
                authors = [{"id": author.id, "name": author.name} for author in result.scalars().all()]

            # Получаем любимые категории
            favorite_categories = await self._get_user_favorite_categories(user_id)
            categories = []
            if favorite_categories:
                query = select(Category).where(Category.id.in_(favorite_categories))
                result = await self.db.execute(query)
                categories = [
                    {"id": category.id, "name": category.name_categories} for category in result.scalars().all()
                ]

            # Получаем любимые теги
            favorite_tags = await self._get_user_favorite_tags(user_id)
            tags = []
            if favorite_tags:
                query = select(Tag).where(Tag.id.in_(favorite_tags))
                result = await self.db.execute(query)
                tags = [{"id": tag.id, "name": tag.name_tag} for tag in result.scalars().all()]

            return {"authors": authors, "categories": categories, "tags": tags}
        except Exception as e:
            logger.error(f"Error in _get_user_preferences: {str(e)}")
            return {"authors": [], "categories": [], "tags": []}
