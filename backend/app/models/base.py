"""
Base model for SQLAlchemy
"""

from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        if cls.__name__.lower()[-1] == "y":
            return cls.__name__.lower()[:-1] + "ies"
        return cls.__name__.lower() + "s"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
