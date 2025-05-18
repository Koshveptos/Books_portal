# Routers Module

## Описание
Модуль содержит маршрутизаторы FastAPI для обработки HTTP-запросов.

## Маршрутизаторы

### books.py
Маршрутизатор для работы с книгами:

```python
@router.get("/books/", response_model=List[BookResponse])
async def get_books(
    skip: int = 0,
    limit: int = 10,
    category_id: Optional[int] = None,
    author_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    sort_by: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получение списка книг с фильтрацией и сортировкой
    """
    pass

@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: Session = Depends(get_db)):
    """
    Получение книги по ID
    """
    pass

@router.post("/books/", response_model=BookResponse)
async def create_book(
    book: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание новой книги
    """
    pass

@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book: BookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновление книги
    """
    pass

@router.delete("/books/{book_id}")
async def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удаление книги
    """
    pass
```

### users.py
Маршрутизатор для работы с пользователями:

```python
@router.get("/users/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе
    """
    pass

@router.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя
    """
    pass

@router.put("/users/me", response_model=UserResponse)
async def update_user(
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновление профиля пользователя
    """
    pass

@router.delete("/users/me")
async def delete_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удаление пользователя
    """
    pass
```

### auth.py
Маршрутизатор для аутентификации:

```python
@router.post("/auth/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Аутентификация пользователя
    """
    pass

@router.post("/auth/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Обновление токена доступа
    """
    pass
```

### recommendations.py
Маршрутизатор для работы с рекомендациями:

```python
@router.get("/recommendations/", response_model=List[BookResponse])
async def get_recommendations(
    limit: int = 10,
    category_id: Optional[int] = None,
    author_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение рекомендаций для пользователя
    """
    pass

@router.get("/recommendations/similar-users", response_model=List[UserResponse])
async def get_similar_users(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение похожих пользователей
    """
    pass
```

## Использование

### Пример работы с маршрутизатором книг
```python
from fastapi import APIRouter, Depends
from app.routers.books import router as books_router

app = FastAPI()
app.include_router(books_router, prefix="/api/v1", tags=["books"])
```

### Пример работы с маршрутизатором пользователей
```python
from fastapi import APIRouter, Depends
from app.routers.users import router as users_router

app = FastAPI()
app.include_router(users_router, prefix="/api/v1", tags=["users"])
```

### Пример работы с маршрутизатором аутентификации
```python
from fastapi import APIRouter, Depends
from app.routers.auth import router as auth_router

app = FastAPI()
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
```

### Пример работы с маршрутизатором рекомендаций
```python
from fastapi import APIRouter, Depends
from app.routers.recommendations import router as recommendations_router

app = FastAPI()
app.include_router(recommendations_router, prefix="/api/v1", tags=["recommendations"])
```
