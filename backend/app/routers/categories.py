from typing import List

from auth import admin_or_moderator
from core.database import get_db
from core.exceptions import CategoryNotFoundException, InvalidCategoryDataException
from core.logger_config import logger
from fastapi import APIRouter, Depends, status
from schemas.book import Category, CategoryCreate, CategoryUpdate
from services.book_servise import CategoryRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["categories"])


@router.post(
    "/", response_model=Category, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_moderator)]
)
async def create_category(category_data: CategoryCreate, session: AsyncSession = Depends(get_db)):
    """Создание новой категории (доступно только для админов и модераторов)"""
    logger.info(f"Creating new category: {category_data.name_categories}")
    try:
        category_repo = CategoryRepository(session)
        category = await category_repo.create(category_data)
        logger.info(f"Category created successfully: {category.name_categories} (id: {category.id})")
        return category
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        raise InvalidCategoryDataException(message=f"Ошибка при создании категории: {str(e)}")


@router.get("/", response_model=List[Category])
async def get_all_categories(session: AsyncSession = Depends(get_db)):
    """Получение списка всех категорий"""
    logger.info("Getting all categories")
    category_repo = CategoryRepository(session)
    categories = await category_repo.get_all()
    logger.info(f"Found {len(categories)} categories")
    return categories


@router.get("/{category_id}", response_model=Category)
async def get_category(category_id: int, session: AsyncSession = Depends(get_db)):
    """Получение категории по ID"""
    logger.info(f"Getting category with id: {category_id}")
    category_repo = CategoryRepository(session)
    category = await category_repo.get_by_id(category_id)
    if not category:
        logger.warning(f"Category not found: id={category_id}")
        raise CategoryNotFoundException(message=f"Категория с ID {category_id} не найдена")
    logger.info(f"Found category: {category.name_categories} (id: {category.id})")
    return category


@router.put("/{category_id}", response_model=Category, dependencies=[Depends(admin_or_moderator)])
async def update_category(category_id: int, category_data: CategoryUpdate, session: AsyncSession = Depends(get_db)):
    """Обновление категории (доступно только для админов и модераторов)"""
    logger.info(f"Updating category with id: {category_id}")
    category_repo = CategoryRepository(session)
    category = await category_repo.update(category_id, category_data)
    if not category:
        logger.warning(f"Category not found for update: id={category_id}")
        raise CategoryNotFoundException(message=f"Категория с ID {category_id} не найдена")
    logger.info(f"Category updated successfully: {category.name_categories} (id: {category.id})")
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_moderator)])
async def delete_category(category_id: int, session: AsyncSession = Depends(get_db)):
    """Удаление категории (доступно только для админов и модераторов)"""
    logger.info(f"Deleting category with id: {category_id}")
    category_repo = CategoryRepository(session)
    result = await category_repo.delete(category_id)
    if not result:
        logger.warning(f"Category not found for deletion: id={category_id}")
        raise CategoryNotFoundException(message=f"Категория с ID {category_id} не найдена")
    logger.info(f"Category deleted successfully: id={category_id}")
    return None
