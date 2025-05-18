from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.book import Book, BookCreate, BookUpdate
from app.services.book_service import BookService

router = APIRouter()


@router.get("/books/", response_model=List[Book])
def get_books(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    author_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    book_service = BookService(db)

    if category_id:
        return book_service.get_books_by_category(category_id, skip, limit)
    elif author_id:
        return book_service.get_books_by_author(author_id, skip, limit)
    elif tag_id:
        return book_service.get_books_by_tag(tag_id, skip, limit)
    elif search:
        return book_service.search_books(search, skip, limit)
    else:
        return book_service.get_books(skip, limit)


@router.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book_service = BookService(db)
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return book


@router.post("/books/", response_model=Book)
def create_book(
    book: BookCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    book_service = BookService(db)
    return book_service.create_book(book)


@router.put("/books/{book_id}", response_model=Book)
def update_book(
    book_id: int,
    book: BookUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    book_service = BookService(db)
    updated_book = book_service.update_book(book_id, book)
    if not updated_book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return updated_book


@router.delete("/books/{book_id}")
def delete_book(
    book_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    if not current_user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    book_service = BookService(db)
    if not book_service.delete_book(book_id):
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return {"message": "Книга успешно удалена"}
