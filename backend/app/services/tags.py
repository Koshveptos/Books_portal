from typing import List, Optional

from models.book import Tag
from schemas.book import TagCreate, TagUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger_config import logger


class TagsService:
    """Service for managing tags in the system."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tags(self) -> List[Tag]:
        """
        Get all tags in the system.

        Returns:
            List of all tags
        """
        query = select(Tag)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_tag_by_id(self, tag_id: int) -> Optional[Tag]:
        """
        Get tag by ID.

        Args:
            tag_id: Tag identifier

        Returns:
            Tag object or None if not found
        """
        query = select(Tag).where(Tag.id == tag_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """
        Get tag by name.

        Args:
            name: Tag name

        Returns:
            Tag object or None if not found
        """
        query = select(Tag).where(Tag.name_tags == name)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def create_tag(self, tag_data: TagCreate) -> Tag:
        """
        Create a new tag.

        Args:
            tag_data: Tag creation data

        Returns:
            Created tag object

        Raises:
            ValueError: If tag with the same name already exists
        """
        # Check if tag with same name already exists
        existing_tag = await self.get_tag_by_name(tag_data.name_tags)
        if existing_tag:
            logger.warning(f"Tag with name '{tag_data.name_tags}' already exists")
            raise ValueError(f"Tag with name '{tag_data.name_tags}' already exists")

        # Create tag
        tag_dict = tag_data.model_dump()
        db_tag = Tag(**tag_dict)

        self.session.add(db_tag)
        await self.session.commit()
        await self.session.refresh(db_tag)

        logger.info(f"Tag created: {db_tag.name_tags} (ID: {db_tag.id})")
        return db_tag

    async def update_tag(self, tag_id: int, tag_data: TagUpdate) -> Optional[Tag]:
        """
        Update tag information.

        Args:
            tag_id: Tag identifier
            tag_data: Tag update data

        Returns:
            Updated tag or None if not found

        Raises:
            ValueError: If tag with the same name already exists
        """
        # Get tag by ID
        tag = await self.get_tag_by_id(tag_id)
        if not tag:
            return None

        # Check name uniqueness if it's changed
        if tag_data.name_tags and tag_data.name_tags != tag.name_tags:
            existing_tag = await self.get_tag_by_name(tag_data.name_tags)
            if existing_tag and existing_tag.id != tag_id:
                logger.warning(f"Tag with name '{tag_data.name_tags}' already exists")
                raise ValueError(f"Tag with name '{tag_data.name_tags}' already exists")

        # Update fields
        update_data = tag_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tag, key, value)

        await self.session.commit()
        await self.session.refresh(tag)

        logger.info(f"Tag updated: {tag.name_tags} (ID: {tag.id})")
        return tag

    async def delete_tag(self, tag_id: int) -> bool:
        """
        Delete a tag by ID.

        Args:
            tag_id: Tag identifier

        Returns:
            True if tag was deleted, False if not found
        """
        tag = await self.get_tag_by_id(tag_id)
        if not tag:
            return False

        await self.session.delete(tag)
        await self.session.commit()

        logger.info(f"Tag deleted: ID {tag_id}")
        return True
