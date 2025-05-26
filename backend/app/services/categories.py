from typing import List, Optional

from models.book import Category
from schemas.book import CategoryCreate, CategoryUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger_config import logger


class CategoriesService:
    """Service for managing categories in the system."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_categories(self) -> List[Category]:
        """
        Get all categories in the system.

        Returns:
            List of all categories
        """
        query = select(Category)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """
        Get category by ID.

        Args:
            category_id: Category identifier

        Returns:
            Category object or None if not found
        """
        query = select(Category).where(Category.id == category_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_category_by_name(self, name: str) -> Optional[Category]:
        """
        Get category by name.

        Args:
            name: Category name

        Returns:
            Category object or None if not found
        """
        query = select(Category).where(Category.name_categories == name)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def create_category(self, category_data: CategoryCreate) -> Category:
        """
        Create a new category.

        Args:
            category_data: Category creation data

        Returns:
            Created category object

        Raises:
            ValueError: If category with the same name already exists
        """
        # Check if category with same name already exists
        existing_category = await self.get_category_by_name(category_data.name_categories)
        if existing_category:
            logger.warning(f"Category with name '{category_data.name_categories}' already exists")
            raise ValueError(f"Category with name '{category_data.name_categories}' already exists")

        # Create category
        category_dict = category_data.model_dump()
        db_category = Category(**category_dict)

        self.session.add(db_category)
        await self.session.commit()
        await self.session.refresh(db_category)

        logger.info(f"Category created: {db_category.name_categories} (ID: {db_category.id})")
        return db_category

    async def update_category(self, category_id: int, category_data: CategoryUpdate) -> Optional[Category]:
        """
        Update category information.

        Args:
            category_id: Category identifier
            category_data: Category update data

        Returns:
            Updated category or None if not found

        Raises:
            ValueError: If category with the same name already exists
        """
        # Get category by ID
        category = await self.get_category_by_id(category_id)
        if not category:
            return None

        # Check name uniqueness if it's changed
        if category_data.name_categories and category_data.name_categories != category.name_categories:
            existing_category = await self.get_category_by_name(category_data.name_categories)
            if existing_category and existing_category.id != category_id:
                logger.warning(f"Category with name '{category_data.name_categories}' already exists")
                raise ValueError(f"Category with name '{category_data.name_categories}' already exists")

        # Update fields
        update_data = category_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(category, key, value)

        await self.session.commit()
        await self.session.refresh(category)

        logger.info(f"Category updated: {category.name_categories} (ID: {category.id})")
        return category

    async def delete_category(self, category_id: int) -> bool:
        """
        Delete a category by ID.

        Args:
            category_id: Category identifier

        Returns:
            True if category was deleted, False if not found
        """
        category = await self.get_category_by_id(category_id)
        if not category:
            return False

        await self.session.delete(category)
        await self.session.commit()

        logger.info(f"Category deleted: ID {category_id}")
        return True
