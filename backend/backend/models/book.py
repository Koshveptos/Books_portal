from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, Column, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Books(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), index=True)
    author: Mapped[str] = mapped_column(String(255))
    year: Mapped[Optional[str]] = mapped_column(String(4), index=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    isbn: Mapped[str] = mapped_column(String(20))
    description: Mapped[Optional[str]] = mapped_column(String(1023))
    cover: Mapped[Optional[str]] = mapped_column(String(255))
    language: Mapped[Optional[str]] = mapped_column(String(50))
    file_url: Mapped[str] = mapped_column(String(255))
    #rating: Mapped[Optional[float]] = mapped_column(default=0.0) 
    #views: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # TODO:
    # add relationship with books and tags and categories
    #category: Mapped[string] = mapped_column
    #tags: Mapped[string] = mapped_column