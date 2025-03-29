from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relations


class Base(DeclarativeBase):
    pass


class Books(Base):
    __tablename__ = "book"

    id:  Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title = Column(String, index=True, nullable=False)
    
