from fastapi_users.db import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from models.base import Base
from sqlalchemy.ext.asyncio import AsyncSession


class User(Base, SQLAlchemyBaseUserTable[int]):

    @classmethod
    def get_db(cls, session: "AsyncSession"):
        return SQLAlchemyUserDatabase(session, User)
