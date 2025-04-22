from fastapi_users.db import SQLAlchemyBaseUserTable
from models.base import Base


class User(Base, SQLAlchemyBaseUserTable[int]):
    pass
    # @classmethod
    # def get_db(cls, session: "AsyncSession"):
    #     return SQLAlchemyUserDatabase(session, User)
