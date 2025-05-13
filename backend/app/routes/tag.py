"""
Маршруты API для тегов книг
"""

from typing import List

from core.auth import current_moderator
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from models.user import User
from schemas.tag import TagCreate, TagResponse, TagUpdate
from services.tags import TagService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=List[TagResponse])
async def get_tags(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список тегов.

    Args:
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поисковый запрос
    """
    try:
        service = TagService(db)
        tags = await service.get_tags(skip=skip, limit=limit, search=search)
        return tags
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка тегов: {str(e)}")


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: int = Path(..., gt=0), db: AsyncSession = Depends(get_db)):
    """
    Получить информацию о теге по ID.

    Args:
        tag_id: ID тега
    """
    try:
        service = TagService(db)
        tag = await service.get_tag(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Тег не найден")
        return tag
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении информации о теге: {str(e)}")


@router.post("/", response_model=TagResponse)
async def create_tag(
    tag_data: TagCreate, current_user: User = Depends(current_moderator), db: AsyncSession = Depends(get_db)
):
    """
    Создать новый тег.

    Args:
        tag_data: Данные для создания тега
    """
    try:
        service = TagService(db)
        tag = await service.create_tag(tag_data)
        return tag
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании тега: {str(e)}")


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int = Path(..., gt=0),
    tag_data: TagUpdate = None,
    current_user: User = Depends(current_moderator),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить информацию о теге.

    Args:
        tag_id: ID тега
        tag_data: Данные для обновления
    """
    try:
        service = TagService(db)
        tag = await service.update_tag(tag_id, tag_data)
        if not tag:
            raise HTTPException(status_code=404, detail="Тег не найден")
        return tag
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении тега: {str(e)}")


@router.delete("/{tag_id}", response_model=bool)
async def delete_tag(
    tag_id: int = Path(..., gt=0), current_user: User = Depends(current_moderator), db: AsyncSession = Depends(get_db)
):
    """
    Удалить тег.

    Args:
        tag_id: ID тега
    """
    try:
        service = TagService(db)
        result = await service.delete_tag(tag_id)
        if not result:
            raise HTTPException(status_code=404, detail="Тег не найден")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении тега: {str(e)}")
