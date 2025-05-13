from typing import List

from auth import admin_or_moderator, check_admin
from core.database import get_db
from core.exceptions import TagNotFoundException
from core.logger_config import logger
from fastapi import APIRouter, Depends, HTTPException, status
from models.book import Tag as TagModel
from models.user import User
from schemas.book import Tag, TagCreate, TagUpdate
from services.book_servise import TagRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["tags"])


@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_moderator)])
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),  # Только модераторы могут создавать теги
):
    """Создание нового тега (доступно только для админов и модераторов)"""
    logger.info(f"Creating new tag: {tag_data.name_tag}")
    try:
        # Проверяем существование тега с таким именем
        stmt = select(TagModel).where(TagModel.name_tag == tag_data.name_tag)
        result = await db.execute(stmt)
        existing_tag = result.scalars().first()

        if existing_tag:
            logger.warning(f"Attempt to create duplicate tag: {tag_data.name_tag}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"Тег с именем '{tag_data.name_tag}' уже существует"
            )

        tag_repo = TagRepository(db)
        tag = await tag_repo.create(tag_data)
        logger.info(f"Tag created successfully: {tag.name_tag} (id: {tag.id})")
        return tag
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating tag: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[Tag])
async def get_all_tags(session: AsyncSession = Depends(get_db)):
    """Получение списка всех тегов"""
    logger.info("Getting all tags")
    tag_repo = TagRepository(session)
    tags = await tag_repo.get_all()
    logger.info(f"Found {len(tags)} tags")
    return tags


@router.get("/{tag_id}", response_model=Tag)
async def get_tag(tag_id: int, session: AsyncSession = Depends(get_db)):
    """Получение тега по ID"""
    logger.info(f"Getting tag with id: {tag_id}")
    tag_repo = TagRepository(session)
    tag = await tag_repo.get_by_id(tag_id)
    if not tag:
        logger.warning(f"Tag not found: id={tag_id}")
        raise TagNotFoundException(message=f"Тег с ID {tag_id} не найден")
    logger.info(f"Found tag: {tag.name_tag} (id: {tag.id})")
    return tag


@router.put("/{tag_id}", response_model=Tag, dependencies=[Depends(admin_or_moderator)])
async def update_tag(tag_id: int, tag_data: TagUpdate, session: AsyncSession = Depends(get_db)):
    """Обновление тега (доступно только для админов и модераторов)"""
    logger.info(f"Updating tag with id: {tag_id}")
    tag_repo = TagRepository(session)
    tag = await tag_repo.update(tag_id, tag_data)
    if not tag:
        logger.warning(f"Tag not found for update: id={tag_id}")
        raise TagNotFoundException(message=f"Тег с ID {tag_id} не найден")
    logger.info(f"Tag updated successfully: {tag.name_tag} (id: {tag.id})")
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_moderator)])
async def delete_tag(tag_id: int, session: AsyncSession = Depends(get_db)):
    """Удаление тега (доступно только для админов и модераторов)"""
    logger.info(f"Deleting tag with id: {tag_id}")
    tag_repo = TagRepository(session)
    result = await tag_repo.delete(tag_id)
    if not result:
        logger.warning(f"Tag not found for deletion: id={tag_id}")
        raise TagNotFoundException(message=f"Тег с ID {tag_id} не найден")
    logger.info(f"Tag deleted successfully: id={tag_id}")
    return None
