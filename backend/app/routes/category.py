"""
Маршруты API для категорий книг
"""

from typing import List

from core.auth import current_moderator
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from models.user import User
from schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from services.categories import CategoriesService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: str = None,
    current_user: User = Depends(current_moderator),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список категорий.

    Args:
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поисковый запрос
    """
    try:
        service = CategoriesService(db)
        categories = await service.get_categories(skip=skip, limit=limit, search=search)
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка категорий: {str(e)}")


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int = Path(..., gt=0),
    current_user: User = Depends(current_moderator),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить информацию о категории по ID.

    Args:
        category_id: ID категории
    """
    try:
        service = CategoriesService(db)
        category = await service.get_category(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        return category
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении информации о категории: {str(e)}")


@router.post("/", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate, current_user: User = Depends(current_moderator), db: AsyncSession = Depends(get_db)
):
    """
    Создать новую категорию.

    Args:
        category_data: Данные для создания категории
    """
    if not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания категории")
    try:
        service = CategoriesService(db)
        category = await service.create_category(category_data)
        return category
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании категории: {str(e)}")


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int = Path(..., gt=0),
    category_data: CategoryUpdate = None,
    current_user: User = Depends(current_moderator),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить информацию о категории.

    Args:
        category_id: ID категории
        category_data: Данные для обновления
    """
    if not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Недостаточно прав для обновления категории")
    try:
        service = CategoriesService(db)
        category = await service.update_category(category_id, category_data)
        if not category:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        return category
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении категории: {str(e)}")


@router.delete("/{category_id}", response_model=bool)
async def delete_category(
    category_id: int = Path(..., gt=0),
    current_user: User = Depends(current_moderator),
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить категорию.

    Args:
        category_id: ID категории
    """
    if not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления категории")
    try:
        service = CategoriesService(db)
        result = await service.delete_category(category_id)
        if not result:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении категории: {str(e)}")
