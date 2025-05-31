"""
Схемы Pydantic для Books Portal API
"""

from schemas.author import AuthorBase, AuthorCreate, AuthorResponse
from schemas.book import BookBase, BookCreate, BookResponse, BookSearchResponse, BookUpdate
from schemas.category import CategoryBase, CategoryCreate, CategoryResponse
from schemas.interactions import FavoriteResponse, LikeResponse, RatingBase, RatingCreate, RatingResponse
from schemas.recommendations import BookRecommendation, RecommendationStats, RecommendationType, SimilarUser
from schemas.tag import TagBase, TagCreate, TagResponse
from schemas.user import ChangeUserStatusRequest, LogoutResponse, TokenResponse, UserCreate, UserRead, UserUpdate

__all__ = [
    "UserRead",
    "UserCreate",
    "UserUpdate",
    "ChangeUserStatusRequest",
    "TokenResponse",
    "LogoutResponse",
    "BookBase",
    "BookCreate",
    "BookResponse",
    "BookUpdate",
    "BookSearchResponse",
    "AuthorBase",
    "AuthorCreate",
    "AuthorResponse",
    "CategoryBase",
    "CategoryCreate",
    "CategoryResponse",
    "TagBase",
    "TagCreate",
    "TagResponse",
    "RatingBase",
    "RatingCreate",
    "RatingResponse",
    "LikeResponse",
    "FavoriteResponse",
    "RecommendationType",
    "BookRecommendation",
    "SimilarUser",
    "RecommendationStats",
]
