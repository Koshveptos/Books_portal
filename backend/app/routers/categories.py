from typing import List

from auth import admin_or_moderator, check_admin
from fastapi import APIRouter, Depends, status
from models.book import Category as CategoryModel
from models.user import User
from schemas.book import Category, CategoryCreate, CategoryUpdate
from services.book_servise import CategoryRepository
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    CategoryNotFoundException,
    DatabaseException,
    InvalidCategoryDataException,
    PermissionDeniedException,
)
from app.core.logger_config import (
    log_db_error,
    log_info,
    log_warning,
)

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

        category_repo = CategoryRepository(db)
        category = await category_repo.create(category_data)
        log_info(f"Category created successfully: {category.name_categories} (id: {category.id})")
        return category
    except (InvalidCategoryDataException, PermissionDeniedException):
        raise
    except IntegrityError as e:
        await db.rollback()
        log_db_error(e, operation="create_category", table="categories")
        raise InvalidCategoryDataException("Ошибка при создании категории")
    except Exception as e:
        await db.rollback()
        log_db_error(e, operation="create_category", table="categories")
        raise DatabaseException("Ошибка при создании категории")


@router.get("/", response_model=List[Category])
async def get_all_categories(session: AsyncSession = Depends(get_db)):
    """Получение списка всех категорий"""
    try:
        log_info("Getting all categories")
        category_repo = CategoryRepository(session)
        categories = await category_repo.get_all()
        log_info(f"Found {len(categories)} categories")
        return categories
    except Exception as e:
        log_db_error(e, operation="get_all_categories", table="categories")
        raise DatabaseException("Ошибка при получении списка категорий")


@router.get("/{category_id}", response_model=Category)
async def get_category(category_id: int, session: AsyncSession = Depends(get_db)):
    """Получение категории по ID"""
    try:
        log_info(f"Getting category with id: {category_id}")
        category_repo = CategoryRepository(session)
        category = await category_repo.get_by_id(category_id)
        if not category:
            log_warning(f"Category not found: id={category_id}")
            raise CategoryNotFoundException(message=f"Категория с ID {category_id} не найдена")
        log_info(f"Found category: {category.name_categories} (id: {category.id})")
        return category
    except CategoryNotFoundException:
        raise
    except Exception as e:
        log_db_error(e, operation="get_category", table="categories", category_id=category_id)
        raise DatabaseException("Ошибка при получении категории")


@router.put("/{category_id}", response_model=Category, dependencies=[Depends(admin_or_moderator)])
async def update_category(category_id: int, category_data: CategoryUpdate, session: AsyncSession = Depends(get_db)):
    """Обновление категории (доступно только для админов и модераторов)"""
    try:
        log_info(f"Updating category with id: {category_id}")
        category_repo = CategoryRepository(session)
        category = await category_repo.update(category_id, category_data)
        if not category:
            log_warning(f"Category not found for update: id={category_id}")
            raise CategoryNotFoundException(message=f"Категория с ID {category_id} не найдена")
        log_info(f"Category updated successfully: {category.name_categories} (id: {category.id})")
        return category
    except (CategoryNotFoundException, PermissionDeniedException):
        raise
    except IntegrityError as e:
        await session.rollback()
        log_db_error(e, operation="update_category", table="categories", category_id=category_id)
        raise InvalidCategoryDataException("Ошибка при обновлении категории")
    except Exception as e:
        await session.rollback()
        log_db_error(e, operation="update_category", table="categories", category_id=category_id)
        raise DatabaseException("Ошибка при обновлении категории")


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_moderator)])
async def delete_category(category_id: int, session: AsyncSession = Depends(get_db)):
    """Удаление категории (доступно только для админов и модераторов)"""
    try:
        log_info(f"Deleting category with id: {category_id}")
        category_repo = CategoryRepository(session)
        result = await category_repo.delete(category_id)
        if not result:
            log_warning(f"Category not found for deletion: id={category_id}")
            raise CategoryNotFoundException(message=f"Категория с ID {category_id} не найдена")
        log_info(f"Category deleted successfully: id={category_id}")
        return None
    except (CategoryNotFoundException, PermissionDeniedException):
        raise
    except Exception as e:
        await session.rollback()
        log_db_error(e, operation="delete_category", table="categories", category_id=category_id)
        raise DatabaseException("Ошибка при удалении категории")
