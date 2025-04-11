"""fix Tag and Category

Revision ID: 47f39d8e50fd
Revises: 47b92dd9ed8e
Create Date: 2025-04-10 02:46:17.642495

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "47f39d8e50fd"
down_revision: Union[str, None] = "47b92dd9ed8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Удаляем старые таблицы связей и зависимости
    op.drop_constraint("books_tags_tag_id_fkey", "books_tags", type_="foreignkey")
    op.drop_constraint("books_tags_book_id_fkey", "books_tags", type_="foreignkey")
    op.drop_constraint("books_categories_categories_id_fkey", "books_categories", type_="foreignkey")
    op.drop_constraint("books_categories_book_id_fkey", "books_categories", type_="foreignkey")

    # 2. Удаляем старые таблицы
    op.drop_index("ix_tegs_name_tag", table_name="tegs")
    op.drop_table("tegs")
    op.drop_index("ix_book_publisher", table_name="book")
    op.drop_index("ix_book_title", table_name="book")
    op.drop_index("ix_book_year", table_name="book")
    op.drop_table("book")

    # 3. Создаем новые таблицы
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=50), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("year", sa.String(length=4), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("isbn", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=1023), nullable=True),
        sa.Column("cover", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("file_url", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_books_publisher"), "books", ["publisher"], unique=False)
    op.create_index(op.f("ix_books_title"), "books", ["title"], unique=False)
    op.create_index(op.f("ix_books_year"), "books", ["year"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name_tag", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_name_tag"), "tags", ["name_tag"], unique=True)

    # 4. Обновляем таблицы связей
    op.add_column("books_categories", sa.Column("category_id", sa.Integer(), nullable=True))
    op.drop_column("books_categories", "categories_id")
    op.create_foreign_key(None, "books_categories", "books", ["book_id"], ["id"])
    op.create_foreign_key(None, "books_categories", "categories", ["category_id"], ["id"])

    op.create_foreign_key(None, "books_tags", "books", ["book_id"], ["id"])
    op.create_foreign_key(None, "books_tags", "tags", ["tag_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Удаляем новые таблицы связей и зависимости
    op.drop_constraint(None, "books_tags", type_="foreignkey")
    op.drop_constraint(None, "books_tags", type_="foreignkey")
    op.drop_constraint(None, "books_categories", type_="foreignkey")
    op.drop_constraint(None, "books_categories", type_="foreignkey")

    # 2. Удаляем новые таблицы
    op.drop_index(op.f("ix_tags_name_tag"), table_name="tags")
    op.drop_table("tags")
    op.drop_index(op.f("ix_books_publisher"), table_name="books")
    op.drop_index(op.f("ix_books_title"), table_name="books")
    op.drop_index(op.f("ix_books_year"), table_name="books")
    op.drop_table("books")

    # 3. Восстанавливаем старые таблицы
    op.create_table(
        "book",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=50), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("year", sa.String(length=4), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("isbn", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=1023), nullable=True),
        sa.Column("cover", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("file_url", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_book_publisher", "book", ["publisher"], unique=False)
    op.create_index("ix_book_title", "book", ["title"], unique=False)
    op.create_index("ix_book_year", "book", ["year"], unique=False)

    op.create_table(
        "tegs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name_tag", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tegs_name_tag", "tegs", ["name_tag"], unique=True)

    # 4. Восстанавливаем таблицы связей
    op.add_column("books_categories", sa.Column("categories_id", sa.Integer(), nullable=True))
    op.drop_column("books_categories", "category_id")
    op.create_foreign_key(
        "books_categories_categories_id_fkey", "books_categories", "categories", ["categories_id"], ["id"]
    )
    op.create_foreign_key("books_categories_book_id_fkey", "books_categories", "book", ["book_id"], ["id"])

    op.create_foreign_key("books_tags_tag_id_fkey", "books_tags", "tegs", ["tag_id"], ["id"])
    op.create_foreign_key("books_tags_book_id_fkey", "books_tags", "book", ["book_id"], ["id"])
