from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.author import Author
from app.models.book import Book
from app.models.category import Category
from app.models.tag import Tag
from app.schemas.book import BookCreate, BookUpdate


class BookService:
    def __init__(self, db: Session):
        self.db = db

    def get_book(self, book_id: int) -> Optional[Book]:
        return self.db.query(Book).filter(Book.id == book_id).first()

    def get_books(self, skip: int = 0, limit: int = 100) -> List[Book]:
        return self.db.query(Book).offset(skip).limit(limit).all()

    def create_book(self, book: BookCreate) -> Book:
        db_book = Book(**book.dict())
        self.db.add(db_book)
        self.db.commit()
        self.db.refresh(db_book)
        return db_book

    def update_book(self, book_id: int, book: BookUpdate) -> Optional[Book]:
        db_book = self.get_book(book_id)
        if db_book:
            for key, value in book.dict(exclude_unset=True).items():
                setattr(db_book, key, value)
            self.db.commit()
            self.db.refresh(db_book)
        return db_book

    def delete_book(self, book_id: int) -> bool:
        db_book = self.get_book(book_id)
        if db_book:
            self.db.delete(db_book)
            self.db.commit()
            return True
        return False

    def get_books_by_category(
        self, category_id: int, skip: int = 0, limit: int = 100
    ) -> List[Book]:
        return (
            self.db.query(Book)
            .join(Category)
            .filter(Category.id == category_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_books_by_author(
        self, author_id: int, skip: int = 0, limit: int = 100
    ) -> List[Book]:
        return (
            self.db.query(Book)
            .join(Author)
            .filter(Author.id == author_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_books_by_tag(
        self, tag_id: int, skip: int = 0, limit: int = 100
    ) -> List[Book]:
        return (
            self.db.query(Book)
            .join(Book.tags)
            .filter(Tag.id == tag_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_books(self, query: str, skip: int = 0, limit: int = 100) -> List[Book]:
        return (
            self.db.query(Book)
            .filter(
                (Book.title.ilike(f"%{query}%"))
                | (Book.description.ilike(f"%{query}%"))
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
