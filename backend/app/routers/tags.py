import json
from typing import List

from auth import admin_or_moderator, check_admin
from fastapi import APIRouter, Depends, HTTPException, status
from models.book import Tag as TagModel
from models.user import User
from redis import Redis
from schemas.book import Tag, TagCreate, TagUpdate
from schemas.tag import TagResponse
from services.book_servise import TagRepository
from services.tags import TagsService
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_redis_client
from app.core.exceptions import (
    DatabaseException,
    InvalidTagDataException,
    PermissionDeniedException,
    TagNotFoundException,
)
from app.core.logger_config import (
    log_cache_error,
    log_db_error,
    log_info,
    log_warning,
)
from app.utils.json_serializer import deserialize_from_json, serialize_to_json

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


@router.get("/", response_model=List[TagResponse])
async def get_tags(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> List[TagResponse]:
    """
    Получение списка всех тегов.

    Args:
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        List[TagResponse]: Список тегов

    Raises:
        HTTPException: Если произошла ошибка при получении тегов
    """
    try:
        # Пытаемся получить из кэша
        if redis_client is not None:
            try:
                cache_key = "tags:all"
                cached_tags = await redis_client.get(cache_key)
                if cached_tags:
                    try:
                        tags_data = deserialize_from_json(cached_tags)
                        log_info("Successfully retrieved all tags from cache")
                        return [TagResponse(**tag) for tag in tags_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_tags",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_tags",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем теги из БД
        tag_service = TagsService(db)
        tags = await tag_service.get_tags()

        # Преобразуем в Pydantic модели
        tag_responses = [TagResponse.model_validate(tag) for tag in tags]

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(tag_responses),
                    expire=3600,  # 1 час
                )
                log_info("Successfully cached all tags")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_tags",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return tag_responses
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_tags",
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении списка тегов"
        )


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> TagResponse:
    """
    Получение тега по ID.

    Args:
        tag_id: ID тега
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        TagResponse: Информация о теге

    Raises:
        HTTPException: Если тег не найден или произошла ошибка
    """
    try:
        # Пытаемся получить из кэша
        if redis_client is not None:
            try:
                cache_key = f"tag:{tag_id}"
                cached_tag = await redis_client.get(cache_key)
                if cached_tag:
                    try:
                        tag_data = deserialize_from_json(cached_tag)
                        log_info(f"Successfully retrieved tag {tag_id} from cache")
                        return TagResponse(**tag_data)
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_tag",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_tag",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем тег из БД
        tag_service = TagsService(db)
        tag = await tag_service.get_tag_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Тег с ID {tag_id} не найден")

        # Преобразуем в Pydantic модель
        tag_response = TagResponse.model_validate(tag)

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(tag_response),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached tag {tag_id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_tag",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return tag_response
    except HTTPException:
        raise
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_tag",
                "tag_id": tag_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении тега")


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
