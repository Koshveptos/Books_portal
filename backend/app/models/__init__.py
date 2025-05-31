"""
Models module for Books Portal API
"""

import logging
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для правильного импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Импортируем базовую модель и все классы
from .base import Base
from .book import (
    Author,
    Book,
    Category,
    Language,
    Rating,
    Tag,
    book_authors,
    books_categories,
    books_tags,
    favorites,
    likes,
)
from .user import User

# Логгер для отслеживания загрузки моделей
logger = logging.getLogger(__name__)


# Функция для инициализации всех моделей
def init_models():
    """
    Инициализация всех моделей и их отношений.
    """
    logger.info("Initializing database models...")

    # Выводим список загруженных моделей
    models = [cls for cls in Base.__subclasses__()]
    logger.info(f"Loaded {len(models)} models: {', '.join([model.__name__ for model in models])}")


# Список всех экспортируемых моделей
__all__ = [
    "Base",
    "User",
    "Book",
    "Author",
    "Category",
    "Tag",
    "Rating",
    "likes",
    "favorites",
    "books_tags",
    "books_categories",
    "book_authors",
    "Language",
    "init_models",
]

# Инициализируем модели при импорте
init_models()
