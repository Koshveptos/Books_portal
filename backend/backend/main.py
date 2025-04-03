from fastapi import FastAPI
from typing import Annotated

import uvicorn



from core.database import AsyncSessionLocal
from routers.books import router as books_router
from core.database import engine, init_db
import asyncio


app = FastAPI()

#потом все подключения роутеров в один файл перекинуть и там настроить все
app.include_router(books_router, prefix='/books', tags=['books'])

@app.get("/")
async def root():
    return {"message": "Welcome to the Books API"}


if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000,log_level="debug")




