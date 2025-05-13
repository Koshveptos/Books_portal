"""
Маршруты API для Books Portal.
"""

from routes.auth import router as auth_router
from routes.book import router as book_router
from routes.category import router as category_router
from routes.interactions import router as interactions_router
from routes.recommendations import router as recommendations_router
from routes.tag import router as tag_router

__all__ = [
    "auth_router",
    "book_router",
    "category_router",
    "tag_router",
    "interactions_router",
    "recommendations_router",
]
