import asyncio

from models.base import Base

from app.core.database import engine


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(init_db())
