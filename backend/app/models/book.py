from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

Base = declarative_base()


class Language(enum.Enum):
    RU = "ru"
    EN = "en"


book_categories = Table(
    "book_categories",
    Base.metadata,
    Column("book_id", ForeignKey("books.id")),
    Column("category_id", ForeignKey("categories.id")),
)

book_tags = Table(
    "book_tags", Base.metadata, Column("book_id", ForeignKey("books.id")), Column("tag_id", ForeignKey("tags.id"))
)

book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", ForeignKey("books.id"), primary_key=True),
    Column("author_id", ForeignKey("authors.id"), primary_key=True),
)


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(50), index=True)
    year: Mapped[str | None] = mapped_column(String(4), index=True)
    publisher: Mapped[str | None] = mapped_column(String(255), index=True)
    isbn: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(1023))
    cover: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[Language] = mapped_column(Enum(Language), nullable=False, default=Language.RU)
    file_url: Mapped[str] = mapped_column(String(255))
    search_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )
    categories: Mapped[list[Category]] = relationship(secondary=book_categories, back_populates="books")
    tags: Mapped[list[Tag]] = relationship(secondary=book_tags, back_populates="books")
    authors: Mapped[list[Author]] = relationship(secondary=book_authors, back_populates="books")


class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    books: Mapped[list[Book]] = relationship(secondary=book_authors, back_populates="authors")
    search_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, nullable=True)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name_categories: Mapped[str] = mapped_column(String(50), index=True, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    books: Mapped[list[Book]] = relationship(secondary=book_categories, back_populates="categories")
    search_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, nullable=True)


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name_tag: Mapped[str] = mapped_column(String(50), index=True, nullable=False, unique=True)
    books: Mapped[list[Book]] = relationship(secondary=book_tags, back_populates="tags")
    search_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, nullable=True)
