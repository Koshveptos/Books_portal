import random
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from models.book import Author, Book, Category, Rating, Tag, favorites, likes
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType
from sqlalchemy import desc, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload


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
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
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
            min_year: Минимальный год издания
            max_year: Максимальный год издания
            min_ratings_count: Минимальное количество оценок
            recommendation_type: Тип рекомендаций
            cache: Использовать ли кэширование
        """
        # Получаем уже оцененные пользователем книги, чтобы исключить их из рекомендаций
        rated_book_ids = await self._get_rated_book_ids(user_id)
        liked_book_ids = await self._get_liked_book_ids(user_id)
        favorited_book_ids = await self._get_favorited_book_ids(user_id)

        # Объединяем все ID книг, которые пользователь уже оценил, лайкнул или добавил в избранное
        exclude_book_ids = set(rated_book_ids) | set(liked_book_ids) | set(favorited_book_ids)

        # Выбираем метод рекомендаций в зависимости от типа
        if recommendation_type == RecommendationType.COLLABORATIVE:
            recommendations = await self._get_collaborative_recommendations(
                user_id, limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
            )
        elif recommendation_type == RecommendationType.CONTENT:
            recommendations = await self._get_content_based_recommendations(
                user_id, limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
            )
        elif recommendation_type == RecommendationType.POPULARITY:
            recommendations = await self._get_popularity_based_recommendations(
                limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
            )
        elif recommendation_type == RecommendationType.AUTHOR:
            recommendations = await self._get_author_based_recommendations(
                user_id, limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
            )
        elif recommendation_type == RecommendationType.CATEGORY:
            recommendations = await self._get_category_based_recommendations(
                user_id, limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
            )
        elif recommendation_type == RecommendationType.TAG:
            recommendations = await self._get_tag_based_recommendations(
                user_id, limit, min_rating, min_year, max_year, min_ratings_count, exclude_book_ids
            )
        else:  # HYBRID - это комбинация всех методов
            recommendations = await self.get_hybrid_recommendations(user_id, limit, exclude_book_ids)

        # Сортируем рекомендации по убыванию оценки и ограничиваем количество
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:limit]

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
        # Получаем оценки текущего пользователя
        user_ratings = await self._get_user_ratings(user_id)

        if not user_ratings:
            return []

        # Получаем всех пользователей, которые оценили хотя бы одну книгу
        query = select(distinct(Rating.user_id))
        result = await self.db.execute(query)
        all_users = [row[0] for row in result.all()]

        # Находим похожих пользователей
        similar_users = []

        for other_user_id in all_users:
            if other_user_id == user_id:
                continue

            # Получаем оценки другого пользователя
            other_user_ratings = await self._get_user_ratings(other_user_id)

            # Находим общие книги
            common_books = set(user_ratings.keys()) & set(other_user_ratings.keys())

            # Находим количество общих оценок
            common_ratings_count = len(common_books)

            if common_ratings_count >= min_common_ratings:
                # Вычисляем косинусное сходство
                similarity = 0

                if common_ratings_count > 0:
                    # Создаем векторы оценок для общих книг
                    user_vector = [user_ratings[book_id] for book_id in common_books]
                    other_vector = [other_user_ratings[book_id] for book_id in common_books]

                    # Вычисляем косинусное сходство
                    similarity = self._calculate_cosine_similarity(user_vector, other_vector)

                # Добавляем пользователя в список, если сходство положительное
                if similarity > 0:
                    similar_users.append({"user_id": other_user_id, "similarity": similarity})

        # Сортируем пользователей по сходству
        similar_users.sort(key=lambda user: user["similarity"], reverse=True)

        return similar_users

    async def _get_book_recommendation_object(self, book: Book, score: float, reason: str) -> BookRecommendation:
        """
        Создать объект рекомендации книги.

        Args:
            book: Объект книги
            score: Оценка рекомендации
            reason: Причина рекомендации
        """
        author_names = [author.name for author in book.authors]
        return BookRecommendation(
            book_id=book.id,
            title=book.title,
            cover=book.cover,
            author_names=author_names,
            year=book.year,
            score=score,
            reason=reason,
        )

    async def _get_collaborative_recommendations(
        self, user_id: int, limit: int = 10, exclude_book_ids: List[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить рекомендации на основе коллаборативной фильтрации.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            exclude_book_ids: Список ID книг, которые нужно исключить

        Returns:
            Список рекомендованных книг с рейтингами и причинами
        """
        # Получаем похожих пользователей
        similar_users = await self._get_similar_users(user_id)

        if not similar_users:
            return []

        # Получаем оценки текущего пользователя
        user_ratings = await self._get_user_ratings(user_id)

        # Исключаем книги, которые пользователь уже оценил или указал в exclude_book_ids
        exclude_ids = await self._get_exclude_book_ids(user_id, exclude_book_ids)

        # Словарь для хранения рекомендаций {book_id: {score: float, similar_users: List[Dict]}}
        book_scores = {}

        # Собираем рейтинги для топ-10 похожих пользователей
        for similar_user in similar_users[:10]:
            similar_user_id = similar_user["user_id"]
            similarity = similar_user["similarity"]

            # Пропускаем пользователей с низким сходством
            if similarity < 0.1:
                continue

            # Получаем оценки похожего пользователя
            similar_user_ratings = await self._get_user_ratings(similar_user_id)

            # Обрабатываем книги, которые оценил похожий пользователь
            for book_id, rating in similar_user_ratings.items():
                # Пропускаем книги, которые уже оценил текущий пользователь или которые нужно исключить
                if book_id in user_ratings or book_id in exclude_ids:
                    continue

                # Инициализируем счетчики для новой книги
                if book_id not in book_scores:
                    book_scores[book_id] = {"weighted_sum": 0, "similarity_sum": 0, "similar_users": []}

                # Добавляем вклад похожего пользователя в оценку книги
                book_scores[book_id]["weighted_sum"] += rating * similarity
                book_scores[book_id]["similarity_sum"] += similarity
                book_scores[book_id]["similar_users"].append(
                    {"user_id": similar_user_id, "similarity": similarity, "rating": rating}
                )

        # Вычисляем итоговые оценки и формируем рекомендации
        recommendations = []

        # Получаем информацию о книгах
        if book_scores:
            book_ids = list(book_scores.keys())
            query = (
                select(Book)
                .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
                .where(Book.id.in_(book_ids))
            )
            result = await self.db.execute(query)
            books = {book.id: book for book in result.scalars().all()}

            # Формируем рекомендации
            for book_id, score_data in book_scores.items():
                if book_id not in books or score_data["similarity_sum"] == 0:
                    continue

                book = books[book_id]
                # Вычисляем итоговую оценку
                predicted_rating = score_data["weighted_sum"] / score_data["similarity_sum"]

                # Для нормализации оценки (от 0 до 1)
                normalized_score = (predicted_rating - 1) / 4  # от 1-5 до 0-1

                # Находим самого похожего пользователя, который оценил эту книгу высоко
                # top_similar_user = max(score_data["similar_users"], key=lambda x: x["similarity"] * x["rating"])

                recommendations.append(
                    {
                        "book": {
                            "id": book.id,
                            "title": book.title,
                            "author": book.author.name if book.author else None,
                            "category": book.category.name if book.category else None,
                            "tags": [tag.name for tag in book.tags],
                            "average_rating": book.average_rating,
                            "ratings_count": book.ratings_count,
                            "cover_image": book.cover_image,
                        },
                        "score": normalized_score,
                        "reason": "Рекомендовано похожими на вас пользователями",
                        "strategy": RecommendationStrategy.COLLABORATIVE,
                        "similar_users": [
                            {"user_id": su["user_id"], "similarity": su["similarity"], "rating": su["rating"]}
                            for su in score_data["similar_users"][:3]  # Включаем только топ-3 похожих пользователей
                        ],
                    }
                )

        # Сортируем по оценке и ограничиваем количество
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:limit]

    async def _get_content_based_recommendations(
        self,
        user_id: int,
        limit: int,
        min_rating: float,
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        """
        Получает рекомендации на основе содержимого (интересы пользователя).

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_year: Минимальный год издания
            max_year: Максимальный год издания
            min_ratings_count: Минимальное количество оценок
            exclude_book_ids: ID книг, которые следует исключить из рекомендаций
        """
        # Получаем любимых авторов, категории и теги пользователя
        favorite_authors = await self._get_user_favorite_authors(user_id)
        favorite_categories = await self._get_user_favorite_categories(user_id)
        favorite_tags = await self._get_user_favorite_tags(user_id)

        if not favorite_authors and not favorite_categories and not favorite_tags:
            return []

        # Строим запрос для получения книг на основе интересов пользователя
        query = (
            select(Book)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .outerjoin(Rating, Rating.book_id == Book.id)
            .group_by(Book.id)
        )

        # Добавляем условия фильтрации
        conditions = []

        if favorite_authors:
            conditions.append(Book.author_id.in_(favorite_authors))

        if favorite_categories:
            conditions.append(Book.category_id.in_(favorite_categories))

        if favorite_tags:
            # Предполагается, что у Book есть отношение многие-ко-многим с Tag
            # Если структура отличается, необходимо адаптировать запрос
            conditions.append(Book.tags.any(Tag.id.in_(favorite_tags)))

        if conditions:
            query = query.where(or_(*conditions))

        # Добавляем фильтры по году
        if min_year:
            query = query.where(Book.publication_year >= min_year)
        if max_year:
            query = query.where(Book.publication_year <= max_year)

        # Исключаем книги, которые пользователь уже взаимодействовал
        if exclude_book_ids:
            query = query.where(Book.id.notin_(exclude_book_ids))

        # Добавляем фильтр по минимальному количеству оценок
        query = query.having(func.count(Rating.id) >= min_ratings_count)

        # Добавляем фильтр по минимальному рейтингу
        query = query.having(func.avg(Rating.rating) >= min_rating)

        # Добавляем сортировку по рейтингу (от высокого к низкому)
        query = query.order_by(desc(func.avg(Rating.rating)))

        # Ограничиваем количество результатов (с запасом)
        query = query.limit(limit * 3)

        # Выполняем запрос
        result = await self.db.execute(query)
        books = result.scalars().all()

        # Создаем рекомендации
        recommendations = []
        for book in books:
            # Получаем средний рейтинг книги
            avg_rating = await self._get_book_avg_rating(book.id)

            # Вычисляем релевантность (score) на основе совпадений интересов
            relevance_score = 0.0

            # Увеличиваем релевантность, если автор в списке любимых
            if book.author_id in favorite_authors:
                relevance_score += 1.0

            # Увеличиваем релевантность, если категория в списке любимых
            if book.category_id in favorite_categories:
                relevance_score += 0.8

            # Увеличиваем релевантность за каждый тег из списка любимых
            for tag in book.tags:
                if tag.id in favorite_tags:
                    relevance_score += 0.5

            # Нормализуем оценку релевантности (от 0 до 1)
            max_possible_score = 1.0 + 0.8 + (0.5 * len(favorite_tags))
            normalized_score = relevance_score / max_possible_score if max_possible_score > 0 else 0

            # Комбинируем релевантность и рейтинг (50/50)
            final_score = (normalized_score * 0.5) + (min(avg_rating / 5.0, 1.0) * 0.5)

            # Создаем рекомендацию
            author_name = book.author.name if book.author else "Неизвестный автор"
            category_name = book.category.name if book.category else "Без категории"

            recommendations.append(
                BookRecommendation(
                    id=book.id,
                    title=book.title,
                    author=author_name,
                    category=category_name,
                    rating=avg_rating,
                    year=book.publication_year,
                    score=final_score,
                    recommendation_type=RecommendationType.CONTENT,
                )
            )

        # Сортируем по релевантности (от высокой к низкой)
        recommendations.sort(key=lambda x: x.score, reverse=True)

        return recommendations[:limit]

    async def get_hybrid_recommendations(
        self, user_id: int, limit: int = 15, exclude_book_ids: List[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить гибридные рекомендации, комбинируя различные методы рекомендаций.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            exclude_book_ids: Список ID книг, которые нужно исключить

        Returns:
            Список рекомендованных книг с рейтингами и причинами
        """
        # Исключаем книги, которые пользователь уже оценил или указал в exclude_book_ids
        exclude_ids = await self._get_exclude_book_ids(user_id, exclude_book_ids)

        # Получаем рекомендации из разных источников
        collaborative_recs = await self._get_collaborative_recommendations(
            user_id, limit=limit // 3, exclude_book_ids=exclude_ids
        )

        # Добавляем книги из collaborative_recs в exclude_ids, чтобы избежать дублирования
        if collaborative_recs:
            exclude_ids.extend([rec["book"]["id"] for rec in collaborative_recs])

        content_recs = await self._get_content_based_recommendations(
            user_id, limit=limit // 3, exclude_book_ids=exclude_ids
        )

        # Добавляем книги из content_recs в exclude_ids, чтобы избежать дублирования
        if content_recs:
            exclude_ids.extend([rec["book"]["id"] for rec in content_recs])

        popularity_recs = await self._get_popularity_based_recommendations(
            limit=limit // 3, exclude_book_ids=exclude_ids
        )

        # Объединяем все рекомендации
        all_recs = collaborative_recs + content_recs + popularity_recs

        # Если рекомендаций не хватает, заполняем их рекомендациями по авторам, категориям и тегам
        if len(all_recs) < limit:
            remaining = limit - len(all_recs)

            exclude_ids.extend([rec["book"]["id"] for rec in all_recs])

            author_recs = await self._get_author_based_recommendations(
                user_id, limit=remaining // 3, exclude_book_ids=exclude_ids
            )

            exclude_ids.extend([rec["book"]["id"] for rec in author_recs])

            category_recs = await self._get_category_based_recommendations(
                user_id, limit=remaining // 3, exclude_book_ids=exclude_ids
            )

            exclude_ids.extend([rec["book"]["id"] for rec in category_recs])

            tag_recs = await self._get_tag_based_recommendations(
                user_id, limit=remaining // 3, exclude_book_ids=exclude_ids
            )

            all_recs.extend(author_recs + category_recs + tag_recs)

        # Сортируем рекомендации по оценке
        all_recs.sort(key=lambda x: x["score"], reverse=True)

        # Убираем дубликаты (по book.id)
        unique_recs = []
        seen_book_ids = set()

        for rec in all_recs:
            book_id = rec["book"]["id"]
            if book_id not in seen_book_ids:
                seen_book_ids.add(book_id)
                # Меняем причину для гибридных рекомендаций
                if rec["strategy"] != RecommendationStrategy.HYBRID:
                    rec["reason"] = f"{rec['reason']} [Гибридная рекомендация]"
                    rec["strategy"] = RecommendationStrategy.HYBRID
                unique_recs.append(rec)

        # Ограничиваем количество
        return unique_recs[:limit]

    async def _get_popularity_based_recommendations(
        self, limit: int = 10, exclude_book_ids: List[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить рекомендации на основе популярности книг.

        Args:
            limit: Максимальное количество рекомендаций
            exclude_book_ids: Список ID книг, которые нужно исключить

        Returns:
            Список рекомендованных книг с рейтингами и причинами
        """
        # Создаем подзапрос для получения среднего рейтинга и количества оценок для каждой книги
        subquery = (
            select(
                Rating.book_id,
                func.avg(Rating.rating).label("avg_rating"),
                func.count(Rating.id).label("ratings_count"),
            )
            .group_by(Rating.book_id)
            .having(func.count(Rating.id) >= 5)  # Минимальное количество оценок
            .having(func.avg(Rating.rating) >= 4.0)  # Минимальный средний рейтинг
            .subquery()
        )

        # Основной запрос для получения книг с высоким рейтингом и фильтрацией
        query = (
            select(Book, subquery.c.avg_rating, subquery.c.ratings_count)
            .options(joinedload(Book.author), joinedload(Book.category), selectinload(Book.tags))
            .join(subquery, Book.id == subquery.c.book_id)
        )

        # Исключаем книги, которые нужно исключить
        if exclude_book_ids:
            query = query.where(Book.id.notin_(exclude_book_ids))

        # Сортируем по рейтингу и количеству оценок (с учетом популярности)
        # Формула: avg_rating * (1 + log10(ratings_count))
        query = query.order_by((subquery.c.avg_rating * (1 + func.log(subquery.c.ratings_count))).desc())

        # Ограничиваем количество результатов
        query = query.limit(limit)

        # Выполняем запрос
        result = await self.db.execute(query)
        rows = result.all()

        # Создаем список рекомендаций
        recommendations = []
        for row in rows:
            book, avg_rating, ratings_count = row

            # Нормализуем оценку (от 0 до 1)
            normalized_score = min(avg_rating / 5.0, 1.0)

            # Добавляем небольшую случайность, чтобы разнообразить рекомендации
            randomized_score = normalized_score * (0.95 + random.random() * 0.1)

            recommendations.append(
                {
                    "book": {
                        "id": book.id,
                        "title": book.title,
                        "author": book.author.name if book.author else None,
                        "category": book.category.name if book.category else None,
                        "tags": [tag.name for tag in book.tags],
                        "average_rating": avg_rating,
                        "ratings_count": ratings_count,
                        "cover_image": book.cover_image,
                    },
                    "score": randomized_score,
                    "reason": f"Популярная книга с высоким рейтингом ({avg_rating:.1f})",
                    "strategy": RecommendationStrategy.POPULARITY,
                }
            )

        return recommendations

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
            categories = [category.name for category in result.scalars().all()]

        # Получаем названия тегов
        tags = []
        if favorite_tags:
            query = select(Tag).where(Tag.id.in_(favorite_tags))
            result = await self.db.execute(query)
            tags = [tag.name for tag in result.scalars().all()]

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
        query = (
            select(Book.author_id)
            .join(Rating, Rating.book_id == Book.id)
            .where(Rating.user_id == user_id, Rating.rating >= 4)
            .group_by(Book.author_id)
            .having(func.count(Book.id) >= 1)
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def _get_user_favorite_categories(self, user_id: int) -> List[int]:
        """Получить ID категорий, книги которых пользователь оценил высоко (>=4)"""
        query = (
            select(Book.category_id)
            .join(Rating, Rating.book_id == Book.id)
            .where(Rating.user_id == user_id, Rating.rating >= 4)
            .group_by(Book.category_id)
            .having(func.count(Book.id) >= 1)
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

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
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        """
        Получает рекомендации на основе любимых авторов пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_year: Минимальный год издания
            max_year: Максимальный год издания
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

        # Добавляем фильтры по году
        if min_year:
            query = query.where(Book.publication_year >= min_year)
        if max_year:
            query = query.where(Book.publication_year <= max_year)

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
            category_name = book.category.name if book.category else "Без категории"

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
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        """
        Получает рекомендации на основе любимых категорий пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_year: Минимальный год издания
            max_year: Максимальный год издания
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

        # Добавляем фильтры по году
        if min_year:
            query = query.where(Book.publication_year >= min_year)
        if max_year:
            query = query.where(Book.publication_year <= max_year)

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
            category_name = book.category.name if book.category else "Без категории"

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
        min_year: Optional[int],
        max_year: Optional[int],
        min_ratings_count: int,
        exclude_book_ids: Set[int],
    ) -> List[BookRecommendation]:
        """
        Получает рекомендации на основе любимых тегов пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            min_rating: Минимальный рейтинг книг
            min_year: Минимальный год издания
            max_year: Максимальный год издания
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
            # Предполагается, что у Book есть отношение многие-ко-многим с Tag
            # Если структура отличается, необходимо адаптировать запрос
            .where(Book.tags.any(Tag.id.in_(favorite_tags)))
        )

        # Добавляем фильтры по году
        if min_year:
            query = query.where(Book.publication_year >= min_year)
        if max_year:
            query = query.where(Book.publication_year <= max_year)

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
            category_name = book.category.name if book.category else "Без категории"

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
                reason_parts.append(f"в категории {book.category.name}")
            if tag_score > 0 and book.tags:
                top_tag = max(book.tags, key=lambda tag: tag_weights.get(tag.id, 0), default=None)
                if top_tag:
                    reason_parts.append(f"с тегом {top_tag.name}")

            reason = "Похоже на книги, которые вам нравятся"
            if reason_parts:
                reason = "Похоже на книги, которые вам нравятся: " + ", ".join(reason_parts)

            recommendations.append(
                {
                    "book": {
                        "id": book.id,
                        "title": book.title,
                        "author": book.author.name if book.author else None,
                        "category": book.category.name if book.category else None,
                        "tags": [tag.name for tag in book.tags],
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
                        "category": book.category.name if book.category else None,
                        "tags": [tag.name for tag in book.tags],
                        "average_rating": book.average_rating,
                        "ratings_count": book.ratings_count,
                        "cover_image": book.cover_image,
                    },
                    "score": score,
                    "reason": f"В категории {book.category.name if book.category else 'Без категории'}, которую вы оценили высоко",
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
            .where(Tag.id.in_(top_tag_ids), Book.id.notin_(exclude_ids if exclude_ids else [0]))
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
                        "category": book.category.name if book.category else None,
                        "tags": [tag.name for tag in book.tags],
                        "average_rating": book.average_rating,
                        "ratings_count": book.ratings_count,
                        "cover_image": book.cover_image,
                    },
                    "score": score,
                    "reason": f"С тегом {top_tag_for_book.name if top_tag_for_book else 'популярным'}, который вам интересен",
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
