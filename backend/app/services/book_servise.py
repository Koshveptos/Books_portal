from core.database import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


class BookService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db
