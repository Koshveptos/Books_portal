from typing import List

from auth import admin_or_moderator, check_admin
from fastapi import APIRouter, Depends, status
from models.book import Tag as TagModel
from models.user import User
from schemas.book import Tag, TagCreate, TagUpdate
from services.book_servise import TagRepository
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    DatabaseException,
    InvalidTagDataException,
    PermissionDeniedException,
    TagNotFoundException,
)
from app.core.logger_config import (
    log_db_error,
    log_info,
    log_warning,
)

router = APIRouter(tags=["tags"])


@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_moderator)])
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin),  # Только модераторы могут создавать теги
):
    """Создание нового тега (доступно только для админов и модераторов)"""
    try:
        log_info(f"Creating new tag: {tag_data.name_tag}")

        # Проверяем существование тега с таким именем
        stmt = select(TagModel).where(TagModel.name_tag == tag_data.name_tag)
        result = await db.execute(stmt)
        existing_tag = result.scalars().first()

        if existing_tag:
            log_warning(f"Attempt to create duplicate tag: {tag_data.name_tag}")
            raise InvalidTagDataException(f"Тег с именем '{tag_data.name_tag}' уже существует")

        tag_repo = TagRepository(db)
        tag = await tag_repo.create(tag_data)
        log_info(f"Tag created successfully: {tag.name_tag} (id: {tag.id})")
        return tag
    except (InvalidTagDataException, PermissionDeniedException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="create_tag", table="tags")
        raise InvalidTagDataException("Ошибка при создании тега")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="create_tag", table="tags")
        raise DatabaseException("Ошибка при создании тега")


@router.get("/", response_model=List[Tag])
async def get_all_tags(session: AsyncSession = Depends(get_db)):
    """Получение списка всех тегов"""
    try:
        log_info("Getting all tags")
        tag_repo = TagRepository(session)
        tags = await tag_repo.get_all()
        log_info(f"Found {len(tags)} tags")
        return tags
    except Exception as e:
        log_db_error(e, operation="get_all_tags", table="tags")
        raise DatabaseException("Ошибка при получении списка тегов")


@router.get("/{tag_id}", response_model=Tag)
async def get_tag(tag_id: int, session: AsyncSession = Depends(get_db)):
    """Получение тега по ID"""
    try:
        log_info(f"Getting tag with id: {tag_id}")
        tag_repo = TagRepository(session)
        tag = await tag_repo.get_by_id(tag_id)
        if not tag:
            log_warning(f"Tag not found: id={tag_id}")
            raise TagNotFoundException(message=f"Тег с ID {tag_id} не найден")
        log_info(f"Found tag: {tag.name_tag} (id: {tag.id})")
        return tag
    except TagNotFoundException:
        raise
    except Exception as e:
        log_db_error(e, operation="get_tag", table="tags", tag_id=tag_id)
        raise DatabaseException("Ошибка при получении тега")


@router.put("/{tag_id}", response_model=Tag, dependencies=[Depends(admin_or_moderator)])
async def update_tag(tag_id: int, tag_data: TagUpdate, session: AsyncSession = Depends(get_db)):
    """Обновление тега (доступно только для админов и модераторов)"""
    try:
        log_info(f"Updating tag with id: {tag_id}")
        tag_repo = TagRepository(session)
        tag = await tag_repo.update(tag_id, tag_data)
        if not tag:
            log_warning(f"Tag not found for update: id={tag_id}")
            raise TagNotFoundException(message=f"Тег с ID {tag_id} не найден")
        log_info(f"Tag updated successfully: {tag.name_tag} (id: {tag.id})")
        return tag
    except (TagNotFoundException, PermissionDeniedException):
        raise
    except IntegrityError as e:
        await session.rollback()
        log_db_error(e, operation="update_tag", table="tags", tag_id=tag_id)
        raise InvalidTagDataException("Ошибка при обновлении тега")
    except Exception as e:
        await session.rollback()
        log_db_error(e, operation="update_tag", table="tags", tag_id=tag_id)
        raise DatabaseException("Ошибка при обновлении тега")


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_moderator)])
async def delete_tag(tag_id: int, session: AsyncSession = Depends(get_db)):
    """Удаление тега (доступно только для админов и модераторов)"""
    try:
        log_info(f"Deleting tag with id: {tag_id}")
        tag_repo = TagRepository(session)
        result = await tag_repo.delete(tag_id)
        if not result:
            log_warning(f"Tag not found for deletion: id={tag_id}")
            raise TagNotFoundException(message=f"Тег с ID {tag_id} не найден")
        log_info(f"Tag deleted successfully: id={tag_id}")
        return None
    except (TagNotFoundException, PermissionDeniedException):
        raise
    except Exception as e:
        await session.rollback()
        log_db_error(e, operation="delete_tag", table="tags", tag_id=tag_id)
        raise DatabaseException("Ошибка при удалении тега")
