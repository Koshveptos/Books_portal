from fastapi import FastAPI
from typing import Annotated



from routers.endpoints.books import router as books_router

app = FastAPI()
#потом все подключения роутеров в один файл перекинуть и там настроить все
app.include_router(books_router, prefix='/books', tags=['books'])

@app.get('/hhh')
def get_hhh():
    return {'404':'s'}






