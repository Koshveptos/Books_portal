from typing import List

from auth import admin_or_moderator
from core.database import get_db
from core.exceptions import InvalidTagDataException, TagNotFoundException
from core.logger_config import logger
from fastapi import APIRouter, Depends, status
from schemas.book import Tag, TagCreate, TagUpdate
from services.book_servise import TagRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["tags"])


@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_moderator)])
async def create_tag(tag_data: TagCreate, session: AsyncSession = Depends(get_db)):
    """Создание нового тега (доступно только для админов и модераторов)"""
    logger.info(f"Creating new tag: {tag_data.name_tag}")
    try:
        tag_repo = TagRepository(session)
        tag = await tag_repo.create(tag_data)
        logger.info(f"Tag created successfully: {tag.name_tag} (id: {tag.id})")
        return tag
    except Exception as e:
        logger.error(f"Error creating tag: {str(e)}")
        raise InvalidTagDataException(message=f"Ошибка при создании тега: {str(e)}")


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
