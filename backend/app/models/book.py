from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Table
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Используем общую Base из models.base
from .base import Base

# Условный импорт для аннотаций типов, чтобы избежать циклических импортов
if TYPE_CHECKING:
    from .user import User


class Language(str, enum.Enum):
    """
    Перечисление языков книг.
    Обратите внимание: значения должны быть в нижнем регистре для PostgreSQL!
    """

    RU = "ru"
    EN = "en"

    def __str__(self):
        return self.value

    @classmethod
    def _missing_(cls, value):
        # Обрабатываем случай, когда передано значение в неправильном регистре
        if isinstance(value, str):
            # Попробуем найти по верхнему регистру
            for member in cls:
                if member.name == value.upper():
                    return member
            # Или по нижнему регистру
            for member in cls:
                if member.value == value.lower():
                    return member
        return None


# Промежуточная таблица для связи многие-ко-многим между книгами и категориями
books_categories = Table(
    "books_categories",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id")),
    Column("category_id", Integer, ForeignKey("categories.id")),
)

# Промежуточная таблица для связи многие-ко-многим между книгами и тегами
books_tags = Table(
    "books_tags",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id")),
    Column("tag_id", Integer, ForeignKey("tags.id")),
)

# Промежуточная таблица для связи многие-ко-многим между книгами и авторами
book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

# Промежуточная таблица для лайков книг пользователями
likes = Table(
    "likes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("book_id", Integer, ForeignKey("books.id"), primary_key=True),
)

# Промежуточная таблица для избранных книг пользователей
favorites = Table(
    "favorites",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("book_id", Integer, ForeignKey("books.id"), primary_key=True),
)


class Rating(Base):
    """Модель для оценок книг пользователями"""

    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Отношения с полными квалифицированными именами
    book: Mapped["Book"] = relationship("Book", back_populates="ratings")
    user: Mapped["User"] = relationship("User", back_populates="ratings", foreign_keys=[user_id])


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    year: Mapped[str | None] = mapped_column(String(4), index=True)
    publisher: Mapped[str | None] = mapped_column(String(255), index=True)
    isbn: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1023))
    cover: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[Language] = mapped_column(
        SAEnum(Language, values_callable=lambda x: [e.value for e in x], name="language"),
        nullable=False,
        default=Language.RU,
    )
    file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    search_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    # Отношения
    categories: Mapped[list["Category"]] = relationship(secondary=books_categories, back_populates="books")
    tags: Mapped[list["Tag"]] = relationship(secondary=books_tags, back_populates="books")
    authors: Mapped[list["Author"]] = relationship(secondary=book_authors, back_populates="books")
    ratings: Mapped[list["Rating"]] = relationship("Rating", back_populates="book")

    # Необходимо для работы с нативными SQL запросами
    __allow_unmapped__ = True
    _metadata: ClassVar[dict] = None


class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), index=True, nullable=False, unique=True)
    books: Mapped[list["Book"]] = relationship(secondary=book_authors, back_populates="authors")
    search_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, nullable=True)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name_categories: Mapped[str] = mapped_column(String(50), index=True, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    books: Mapped[list["Book"]] = relationship(secondary=books_categories, back_populates="categories")
    search_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, nullable=True)


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name_tag: Mapped[str] = mapped_column(String(50), index=True, nullable=False, unique=True)
    books: Mapped[list["Book"]] = relationship(secondary=books_tags, back_populates="tags")
    search_vector: Mapped[TSVECTOR | None] = mapped_column(TSVECTOR, nullable=True)
