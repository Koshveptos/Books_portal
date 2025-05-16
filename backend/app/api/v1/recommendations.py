from typing import List, Optional

from core.database import get_db
from core.dependencies import get_current_user
from core.logger_config import logger
from fastapi import APIRouter, Depends, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from models.user import User
from schemas.recommendations import BookRecommendation, RecommendationType
from services.recommendations import RecommendationService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/", response_model=List[BookRecommendation])
async def get_recommendations(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    min_rating: float = 3.0,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_ratings_count: int = 5,
    recommendation_type: RecommendationType = RecommendationType.HYBRID,
    use_cache: bool = True,
):
    """
    Получить персональные рекомендации книг.
    """
    try:
        service = RecommendationService(db)
        recommendations = await service.get_user_recommendations(
            user_id=current_user.id,
            limit=limit,
            min_rating=min_rating,
            min_year=min_year,
            max_year=max_year,
            min_ratings_count=min_ratings_count,
            recommendation_type=recommendation_type,
            cache=use_cache,
        )

        if not recommendations:
            return Response(status_code=204)

        # Преобразуем рекомендации в JSON-совместимый формат
        json_recommendations = jsonable_encoder(recommendations)

        # Создаем ответ с явным указанием кодировки
        return JSONResponse(
            content=json_recommendations,
            media_type="application/json; charset=utf-8",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {str(e)}", exc_info=True)
        await db.rollback()
        return JSONResponse(
            status_code=500,
            content={"message": "Ошибка сервера при получении рекомендаций"},
            media_type="application/json; charset=utf-8",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
