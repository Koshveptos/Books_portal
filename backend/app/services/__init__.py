"""Services module for Books Portal API"""

from services.book import BookService
from services.interactions import InteractionsService
from services.recommendation import RecommendationService

__all__ = ["BookService", "InteractionsService", "RecommendationService"]
