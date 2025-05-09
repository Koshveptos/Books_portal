from core.database import get_db
from core.logger_config import logger
from fastapi import Depends
from models.book import Author, Category, Tag
from schemas.book import AuthorCreate, AuthorUpdate, CategoryCreate, CategoryUpdate, TagCreate, TagUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class BookService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db


class AuthorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, author_data: AuthorCreate) -> Author:
        try:
            logger.debug(f"Creating author with data: {author_data.dict()}")
            db_author = Author(name=author_data.name)
            self.session.add(db_author)
            await self.session.commit()
            await self.session.refresh(db_author)
            logger.debug(f"Author created with ID: {db_author.id}")
            return db_author
        except Exception as e:
            logger.error(f"Error in AuthorRepository.create: {str(e)}")
            await self.session.rollback()
            raise

    async def get_all(self):
        result = await self.session.execute(select(Author))
        return result.scalars().all()

    async def get_by_id(self, author_id: int):
        result = await self.session.execute(select(Author).where(Author.id == author_id))
        return result.scalar_one_or_none()

    async def update(self, author_id: int, author_data: AuthorUpdate) -> Author:
        db_author = await self.get_by_id(author_id)
        if not db_author:
            return None

        update_data = author_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_author, key, value)

        await self.session.commit()
        await self.session.refresh(db_author)
        return db_author

    async def delete(self, author_id: int) -> bool:
        db_author = await self.get_by_id(author_id)
        if not db_author:
            return False

        await self.session.delete(db_author)
        await self.session.commit()
        return True


class CategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, category_data: CategoryCreate) -> Category:
        db_category = Category(name_categories=category_data.name_categories, description=category_data.description)
        self.session.add(db_category)
        await self.session.commit()
        await self.session.refresh(db_category)
        return db_category

    async def get_all(self):
        result = await self.session.execute(select(Category))
        return result.scalars().all()

    async def get_by_id(self, category_id: int):
        result = await self.session.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    async def update(self, category_id: int, category_data: CategoryUpdate) -> Category:
        db_category = await self.get_by_id(category_id)
        if not db_category:
            return None

        update_data = category_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_category, key, value)

        await self.session.commit()
        await self.session.refresh(db_category)
        return db_category

    async def delete(self, category_id: int) -> bool:
        db_category = await self.get_by_id(category_id)
        if not db_category:
            return False

        await self.session.delete(db_category)
        await self.session.commit()
        return True


class TagRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tag_data: TagCreate) -> Tag:
        db_tag = Tag(name_tag=tag_data.name_tag)
        self.session.add(db_tag)
        await self.session.commit()
        await self.session.refresh(db_tag)
        return db_tag

    async def get_all(self):
        result = await self.session.execute(select(Tag))
        return result.scalars().all()

    async def get_by_id(self, tag_id: int):
        result = await self.session.execute(select(Tag).where(Tag.id == tag_id))
        return result.scalar_one_or_none()

    async def update(self, tag_id: int, tag_data: TagUpdate) -> Tag:
        db_tag = await self.get_by_id(tag_id)
        if not db_tag:
            return None

        update_data = tag_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_tag, key, value)

        await self.session.commit()
        await self.session.refresh(db_tag)
        return db_tag

    async def delete(self, tag_id: int) -> bool:
        db_tag = await self.get_by_id(tag_id)
        if not db_tag:
            return False

        await self.session.delete(db_tag)
        await self.session.commit()
        return True
