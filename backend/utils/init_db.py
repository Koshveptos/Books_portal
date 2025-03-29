import asyncio

from core.database import engine
from models.users import Base

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init())