from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Result
from sqlalchemy import select, delete
from models.book import Book, Category, Tag
from schemas.book import Book as BookSchema, BookCreate, BookUpdate, BookPartial, CategoryCreate, TagCreate
from core.database import get_db
router = APIRouter()

#@router.get("/{id}")
#def get_book():
#    return {"ну рыбает и хули спотришь":"lol"}
# TODO:
# добавить views для обработки логики, но ток если роутов встанет многовато

@router.get('/',response_model= list[BookSchema])
async def get_books(db:AsyncSession = Depends(get_db)):
    """
    Получить список всех книг.
    """
    try:
        query = select(Book).order_by(Book.id)
        result: Result = await db.execute(query)
        books = result.scalars().all()
        return list(books)
    except Exception as e:
        print(f'Error: {str(e)}')
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get('/{book_id}', response_model=BookSchema )
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получить книгу по её ID.
    """
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

    
@router.post("/",response_model = BookSchema)
async def create_book(book: BookCreate, db:AsyncSession = Depends(get_db)):
    """
    Создать новую книгу.
    """
    try:
        db_book = Book(**book.model_dump())
        db.add(db_book)
        await db.commit()
        await db.refresh(db_book)
        return db_book
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Book already exists")
    except Exception as e:
        await db.rollback()
        print(f'Error: {str(e)}')
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.put('/{book_id}',response_model= BookSchema )
async def update_book(book_id: int, book_update: BookUpdate, db: AsyncSession = Depends(get_db)):
    """
    Полностью обновить книгу по её ID.
    """
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    for name, value in book_update.model_dump().items():
        setattr(book, name, value)
    await db.commit()
    await db.refresh(book)
    return book

           

@router.patch("/{book_id}", response_model=BookSchema)
async def partial_update_book(book_id: int, book_update: BookPartial, db: AsyncSession = Depends(get_db)):
    """
    Частично обновить книгу по её ID.
    """
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Обновляем только указанные поля
    for name, value in book_update.model_dump(exclude_unset=True).items():
        setattr(book, name, value)

    await db.commit()
    await db.refresh(book)
    return book


@router.delete("/{book_id}", response_model=dict)
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удалить книгу по её ID.
    """
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    await db.delete(book)
    await db.commit()
    return {"message": "Book deleted successfully"}



@router.post('/category', response_model=CategoryCreate)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """
    Создать категорию.
    """
    category_db = Category(**category.model_dump())
    db.add(category_db)
    await db.commit()
    await db.refresh(category_db)
    return category_db


@router.post('/tag',response_model=TagCreate)
async def create_tag(tag: TagCreate, db: AsyncSession = Depends(get_db)):
    """
    Создать тег.
    """
    tag_db = Tag(**tag.model_dump())
    db.add(tag_db)
    await db.commit()
    await db.refresh(tag_db)
    return tag_db