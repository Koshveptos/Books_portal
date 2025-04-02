from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.book import Books
from schemas.book import BookCreate
from core.database import get_db
from sqlalchemy.exc import IntegrityError


router = APIRouter()

#@router.get("/{id}")
#def get_book():
#    return {"ну рыбает и хули спотришь":"lol"}



@router.put("/",response_model = BookCreate)
async def create_book(book: BookCreate, db:AsyncSession = Depends(get_db)):
    try:
        db_book = Books(**book.model_dump())
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



