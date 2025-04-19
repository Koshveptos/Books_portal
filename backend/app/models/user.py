from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable

from app.models.base import Base


class UserTable(Base, SQLAlchemyBaseUserTable[int]):
    pass
