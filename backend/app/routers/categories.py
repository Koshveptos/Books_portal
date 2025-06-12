import json
from typing import List

from auth import admin_or_moderator, check_admin
from fastapi import APIRouter, Depends, HTTPException, status
from models.book import Category as CategoryModel
from models.user import User
from redis import Redis
from schemas.book import Category, CategoryCreate, CategoryUpdate
from schemas.category import CategoryResponse
from services.categories import CategoriesService
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_redis_client
from app.core.exceptions import (
    CategoryNotFoundException,
    DatabaseException,
    InvalidCategoryDataException,
    PermissionDeniedException,
)
from app.core.logger_config import (
    log_cache_error,
    log_db_error,
    log_info,
    log_warning,
)
from app.utils.json_serializer import deserialize_from_json, serialize_to_json

router = APIRouter(tags=["categories"])


@router.post(
    "/", response_model=Category, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_moderator)]
)
async def create_category(
    category_data: CategoryCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(check_admin)
):
    """Создание новой категории (доступно только для админов и модераторов)"""
    try:
        log_info(f"Creating new category: {category_data.name_categories}")

        # Проверяем существование категории с таким именем
        stmt = select(CategoryModel).where(CategoryModel.name_categories == category_data.name_categories)
        result = await db.execute(stmt)
        existing_category = result.scalars().first()

        if existing_category:
            log_warning(f"Attempt to create duplicate category: {category_data.name_categories}")
            raise InvalidCategoryDataException(f"Категория с именем '{category_data.name_categories}' уже существует")

        category_service = CategoriesService(db)
        category = await category_service.create_category(category_data)
        log_info(f"Category created successfully: {category.name_categories} (id: {category.id})")
        return category
    except (InvalidCategoryDataException, PermissionDeniedException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="create_category", table="categories", category_name=category_data.name_categories)
        raise InvalidCategoryDataException("Ошибка целостности данных при создании категории")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="create_category", table="categories", category_name=category_data.name_categories)
        raise DatabaseException("Непредвиденная ошибка при создании категории")


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> List[CategoryResponse]:
    """
    Получение списка всех категорий.

    Args:
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        List[CategoryResponse]: Список категорий

    Raises:
        HTTPException: Если произошла ошибка при получении категорий
    """
    try:
        # Пытаемся получить из кэша
        if redis_client is not None:
            try:
                cache_key = "categories:all"
                cached_categories = await redis_client.get(cache_key)
                if cached_categories:
                    try:
                        categories_data = deserialize_from_json(cached_categories)
                        log_info("Successfully retrieved all categories from cache")
                        return [CategoryResponse(**cat) for cat in categories_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_categories",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_categories",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем категории из БД
        category_service = CategoriesService(db)
        categories = await category_service.get_all_categories()

        # Преобразуем в Pydantic модели
        category_responses = [CategoryResponse.model_validate(cat) for cat in categories]

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(category_responses),
                    expire=3600,  # 1 час
                )
                log_info("Successfully cached all categories")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_categories",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return category_responses
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_categories",
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении списка категорий"
        )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> CategoryResponse:
    """
    Получение категории по ID.

    Args:
        category_id: ID категории
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        CategoryResponse: Информация о категории

    Raises:
        HTTPException: Если категория не найдена или произошла ошибка
    """
    try:
        # Пытаемся получить из кэша
        if redis_client is not None:
            try:
                cache_key = f"category:{category_id}"
                cached_category = await redis_client.get(cache_key)
                if cached_category:
                    try:
                        category_data = deserialize_from_json(cached_category)
                        log_info(f"Successfully retrieved category {category_id} from cache")
                        return CategoryResponse(**category_data)
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_category",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_category",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем категорию из БД
        category_service = CategoriesService(db)
        category = await category_service.get_category(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Категория с ID {category_id} не найдена"
            )

        # Преобразуем в Pydantic модель
        category_response = CategoryResponse.model_validate(category)

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(category_response),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached category {category_id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_category",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return category_response
    except HTTPException:
        raise
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_category",
                "category_id": category_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении категории")


@router.put("/{category_id}", response_model=Category, dependencies=[Depends(admin_or_moderator)])
async def update_category(category_id: int, category_data: CategoryUpdate, session: AsyncSession = Depends(get_db)):
    """Обновление категории (доступно только для админов и модераторов)"""
    try:
        log_info(f"Updating category with id: {category_id}")

        # Проверяем существование категории с таким именем
        if category_data.name_categories:
            stmt = select(CategoryModel).where(
                CategoryModel.name_categories == category_data.name_categories, CategoryModel.id != category_id
            )
            result = await session.execute(stmt)
            existing_category = result.scalars().first()

            if existing_category:
                log_warning(f"Attempt to update category to duplicate name: {category_data.name_categories}")
                raise InvalidCategoryDataException(
                    f"Категория с именем '{category_data.name_categories}' уже существует"
                )

        category_service = CategoriesService(session)
        category = await category_service.update_category(category_id, category_data)
        if not category:
            log_warning(f"Category not found for update: id={category_id}")
            raise CategoryNotFoundException(message=f"Категория с ID {category_id} не найдена")
        log_info(f"Category updated successfully: {category.name_categories} (id: {category.id})")
        return category
    except (CategoryNotFoundException, PermissionDeniedException, InvalidCategoryDataException):
        raise
    except IntegrityError as e:
        await session.rollback()
        log_db_error(e, operation="update_category", table="categories", category_id=str(category_id))
        raise InvalidCategoryDataException("Ошибка целостности данных при обновлении категории")
    except Exception as e:
        await session.rollback()
        log_db_error(e, operation="update_category", table="categories", category_id=str(category_id))
        raise DatabaseException("Непредвиденная ошибка при обновлении категории")


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_moderator)])
async def delete_category(category_id: int, session: AsyncSession = Depends(get_db)):
    """Удаление категории (доступно только для админов и модераторов)"""
    try:
        log_info(f"Deleting category with id: {category_id}")

        # Проверяем существование категории перед удалением
        category_service = CategoriesService(session)
        category = await category_service.get_category(category_id)
        if not category:
            log_warning(f"Category not found for deletion: id={category_id}")
            raise CategoryNotFoundException(message=f"Категория с ID {category_id} не найдена")

        result = await category_service.delete_category(category_id)
        if not result:
            log_warning(f"Failed to delete category: id={category_id}")
            raise DatabaseException("Не удалось удалить категорию")

        log_info(f"Category deleted successfully: id={category_id}")
        return None
    except (CategoryNotFoundException, PermissionDeniedException):
        raise
    except IntegrityError as e:
        await session.rollback()
        log_db_error(e, operation="delete_category", table="categories", category_id=str(category_id))
        raise InvalidCategoryDataException("Невозможно удалить категорию, так как она используется в книгах")
    except Exception as e:
        await session.rollback()
        log_db_error(e, operation="delete_category", table="categories", category_id=str(category_id))
        raise DatabaseException("Непредвиденная ошибка при удалении категории")
