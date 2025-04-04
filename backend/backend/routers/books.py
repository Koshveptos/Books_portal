from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.book import Book
from schemas.book import Book as BookSchema
from schemas.book import BookCreate, BookUpdate, BookBase, BookPartial
from core.database import get_db
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Result
from sqlalchemy import select
router = APIRouter()

#@router.get("/{id}")
#def get_book():
#    return {"ну рыбает и хули спотришь":"lol"}
# TODO:
# добавить views для обработки логики, но ток если роутов встанет многовато

@router.get('/',response_model= list[BookSchema])
async def get_books(db:AsyncSession = Depends(get_db)):
    tmp = select(Book).order_by(Book.id)
    result: Result = await db.execute(tmp)
    books = result.scalars().all()
    return list(books)


@router.get('/{book_id}', response_model=BookSchema | None)#+
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

    
@router.post("/",response_model = BookCreate)
async def create_book(book: BookCreate, db:AsyncSession = Depends(get_db)):
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
        raise HTTPException(status_code=500, detail="Internal Server Error")
##посоветоваться, может быстрее и лучше старую книгу по id брать из бд, а не тащить с фронта в запросе
#и нужно ли разделять на две функции частичное обновление или полное или можно и в одной
@router.put('/{book_id}',response_model= BookBase )
async def update_book(book: BookSchema,book_update:BookUpdate | BookPartial,partial: bool = False, db:AsyncSession = Depends(get_db)):
    #exclude_none=True
    for name, value in book_update.model_dump(exclude_unset=partial).items():
        setattr(book, name, value)
    await db.commit()
    return book

           
@router.delete('/',response_model= BookBase | None)
async def delete_book(book: BookSchema, db: AsyncSession = Depends(get_db)): 
    await db.delete(book)
    await db.commit() 