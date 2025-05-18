from core.database import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship


class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # biography = Column(Text, nullable=True)
    # birth_date = Column(DateTime, nullable=True)
    # death_date = Column(DateTime, nullable=True)
    # created_at = Column(DateTime, default=datetime.utcnow)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Отношения
    books = relationship("Book", back_populates="author")
