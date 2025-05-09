from typing import List, Optional

from core.logger_config import logger
from models.book import Author
from schemas.book import AuthorCreate, AuthorUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AuthorsService:
    """Service for managing authors in the system."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_authors(self) -> List[Author]:
        """
        Get all authors in the system.

        Returns:
            List of all authors
        """
        query = select(Author)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_author_by_id(self, author_id: int) -> Optional[Author]:
        """
        Get author by ID.

        Args:
            author_id: Author identifier

        Returns:
            Author object or None if not found
        """
        query = select(Author).where(Author.id == author_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_author_by_name(self, name: str) -> Optional[Author]:
        """
        Get author by name.

        Args:
            name: Author name

        Returns:
            Author object or None if not found
        """
        query = select(Author).where(Author.name == name)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def create_author(self, author_data: AuthorCreate) -> Author:
        """
        Create a new author.

        Args:
            author_data: Author creation data

        Returns:
            Created author object

        Raises:
            ValueError: If author with the same name already exists
        """
        # Check if author with same name already exists
        existing_author = await self.get_author_by_name(author_data.name)
        if existing_author:
            logger.warning(f"Author with name '{author_data.name}' already exists")
            raise ValueError(f"Author with name '{author_data.name}' already exists")

        # Create author
        author_dict = author_data.model_dump()
        db_author = Author(**author_dict)

        self.session.add(db_author)
        await self.session.commit()
        await self.session.refresh(db_author)

        logger.info(f"Author created: {db_author.name} (ID: {db_author.id})")
        return db_author

    async def update_author(self, author_id: int, author_data: AuthorUpdate) -> Optional[Author]:
        """
        Update author information.

        Args:
            author_id: Author identifier
            author_data: Author update data

        Returns:
            Updated author or None if not found

        Raises:
            ValueError: If author with the same name already exists
        """
        # Get author by ID
        author = await self.get_author_by_id(author_id)
        if not author:
            return None

        # Check name uniqueness if it's changed
        if author_data.name and author_data.name != author.name:
            existing_author = await self.get_author_by_name(author_data.name)
            if existing_author and existing_author.id != author_id:
                logger.warning(f"Author with name '{author_data.name}' already exists")
                raise ValueError(f"Author with name '{author_data.name}' already exists")

        # Update fields
        update_data = author_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(author, key, value)

        await self.session.commit()
        await self.session.refresh(author)

        logger.info(f"Author updated: {author.name} (ID: {author.id})")
        return author

    async def delete_author(self, author_id: int) -> bool:
        """
        Delete an author by ID.

        Args:
            author_id: Author identifier

        Returns:
            True if author was deleted, False if not found
        """
        author = await self.get_author_by_id(author_id)
        if not author:
            return False

        await self.session.delete(author)
        await self.session.commit()

        logger.info(f"Author deleted: ID {author_id}")
        return True
