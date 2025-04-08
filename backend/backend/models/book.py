from __future__ import annotations
from datetime import datetime, UTC
from typing import List, Optional
from sqlalchemy import ForeignKey, Column, Integer, String, DateTime, Table
from sqlalchemy.orm import  Mapped, mapped_column, relationship
from models.base import Base



book_categories =  Table(
    "books_categories",
    Base.metadata,
    Column('book_id' , ForeignKey('book.id')),
    Column('categories_id', ForeignKey('categories.id'))
)

book_tags =  Table(
    "books_tags",
    Base.metadata,
    Column('book_id' , ForeignKey('book.id')),
    Column('tag_id', ForeignKey('tegs.id'))
)

class Book(Base):
   # id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), index=True)
    author: Mapped[str] = mapped_column(String(255))
    year: Mapped[Optional[str]] = mapped_column(String(4), index=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    isbn: Mapped[str] = mapped_column(String(20))
    description: Mapped[Optional[str]] = mapped_column(String(1023))
    cover: Mapped[Optional[str]] = mapped_column(String(255))
    language: Mapped[Optional[str]] = mapped_column(String(50))
    file_url: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), nullable=False)
    #rating: Mapped[Optional[float]] = mapped_column(default=0.0) /
    #views: Mapped[int] = mapped_column(default=0)
    categories: Mapped[List[categories]] = relationship( secondary=book_categories, back_populates='books')
    teg: Mapped[List[tegs]] = relationship( secondary=book_tags, back_populates='books')
   
   


class categories(Base):
    name_categories: Mapped[str] = mapped_column(String(50), index=True,nullable=False, unique=True )
    description:Mapped[Optional[str] ] = mapped_column(String(255))
    book:Mapped[List[Book]] = relationship(
        secondary=book_categories,back_populates='categories'
    )


class tegs(Base):
    name_tag: Mapped[str] = mapped_column(String(50),index=True, nullable=False, unique=True )
    book:Mapped[List[Book]] = relationship(
        secondary=book_tags, back_populates='tegs'
    ) 

    