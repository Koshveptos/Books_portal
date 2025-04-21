from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

book_categories = Table(
    "books_categories",
    Base.metadata,
    Column("book_id", ForeignKey("books.id")),
    Column("category_id", ForeignKey("categories.id")),
)

book_tags = Table(
    "books_tags", Base.metadata, Column("book_id", ForeignKey("books.id")), Column("tag_id", ForeignKey("tags.id"))
)


class Book(Base):
    # id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), index=True)
    author: Mapped[str] = mapped_column(String(255))
    year: Mapped[str | None] = mapped_column(String(4), index=True)
    publisher: Mapped[str | None] = mapped_column(String(255), index=True)
    isbn: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(1023))
    cover: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str | None] = mapped_column(String(50))
    file_url: Mapped[str] = mapped_column(String(255))
    # Время создания (устанавливается один раз при создании записи)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Время обновления (обновляется при каждом изменении записи)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )
    # rating: Mapped[Optional[float]] = mapped_column(default=0.0) /
    # views: Mapped[int] = mapped_column(default=0)
    categories: Mapped[list[Category]] = relationship(secondary=book_categories, back_populates="books")
    tags: Mapped[list[Tag]] = relationship(secondary=book_tags, back_populates="books")


class Category(Base):
    name_categories: Mapped[str] = mapped_column(String(50), index=True, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    books: Mapped[list[Book]] = relationship(secondary=book_categories, back_populates="categories")


class Tag(Base):
    name_tag: Mapped[str] = mapped_column(String(50), index=True, nullable=False, unique=True)
    books: Mapped[list[Book]] = relationship(secondary=book_tags, back_populates="tags")
