## переписать все веремное

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine
from models.base import Base
from core.config import settings
async def init_db(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
#DB_HOST = 'localhost'
#DB_PORT = '5432'
#DB_NAME = 'books_portal'
#DB_USER = 'postgres'
#DB_PASSWORD = '12345678'

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Dependency to get database session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session