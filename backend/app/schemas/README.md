# Schemas Module

## Описание
Модуль содержит Pydantic схемы для валидации данных и сериализации/десериализации.

## Схемы

### book.py
Схемы для работы с книгами и связанными сущностями:

#### BookBase
```python
class BookBase(BaseModel):
    title: str
    description: str
    publication_year: int
    language: str
    page_count: int
```

#### BookCreate
```python
class BookCreate(BookBase):
    authors: list[int]
    categories: list[int]
    tags: list[int]
```

#### BookUpdate
```python
class BookUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    publication_year: Optional[int] = None
    language: Optional[str] = None
    page_count: Optional[int] = None
    authors: Optional[list[int]] = None
    categories: Optional[list[int]] = None
    tags: Optional[list[int]] = None
```

#### BookResponse
```python
class BookResponse(BookBase):
    id: int
    rating: float
    ratings_count: int
    created_at: datetime
    updated_at: datetime
    authors: list[AuthorResponse]
    categories: list[CategoryResponse]
    tags: list[TagResponse]

    class Config:
        from_attributes = True
```

#### AuthorBase
```python
class AuthorBase(BaseModel):
    name: str
    biography: Optional[str] = None
```

#### AuthorCreate
```python
class AuthorCreate(AuthorBase):
    pass
```

#### AuthorUpdate
```python
class AuthorUpdate(BaseModel):
    name: Optional[str] = None
    biography: Optional[str] = None
```

#### AuthorResponse
```python
class AuthorResponse(AuthorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

#### CategoryBase
```python
class CategoryBase(BaseModel):
    name_categories: str
```

#### CategoryCreate
```python
class CategoryCreate(CategoryBase):
    pass
```

#### CategoryUpdate
```python
class CategoryUpdate(BaseModel):
    name_categories: Optional[str] = None
```

#### CategoryResponse
```python
class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

#### TagBase
```python
class TagBase(BaseModel):
    name_tag: str
```

#### TagCreate
```python
class TagCreate(TagBase):
    pass
```

#### TagUpdate
```python
class TagUpdate(BaseModel):
    name_tag: Optional[str] = None
```

#### TagResponse
```python
class TagResponse(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### user.py
Схемы для работы с пользователями:

#### UserBase
```python
class UserBase(BaseModel):
    email: str
```

#### UserCreate
```python
class UserCreate(UserBase):
    password: str
```

#### UserUpdate
```python
class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
```

#### UserResponse
```python
class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### rating.py
Схемы для работы с рейтингами:

#### RatingBase
```python
class RatingBase(BaseModel):
    rating: float
```

#### RatingCreate
```python
class RatingCreate(RatingBase):
    book_id: int
```

#### RatingUpdate
```python
class RatingUpdate(BaseModel):
    rating: Optional[float] = None
```

#### RatingResponse
```python
class RatingResponse(RatingBase):
    id: int
    user_id: int
    book_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

## Использование

### Валидация данных
```python
# Создание книги
book_data = {
    "title": "Название книги",
    "description": "Описание книги",
    "publication_year": 2023,
    "language": "ru",
    "page_count": 300,
    "authors": [1, 2],
    "categories": [1, 2],
    "tags": [1, 2]
}
book = BookCreate(**book_data)
```

### Сериализация данных
```python
# Преобразование модели в схему
book_response = BookResponse.model_validate(book)
```

### Десериализация данных
```python
# Преобразование схемы в словарь
book_dict = book_response.model_dump()
```

### Валидация с дополнительными правилами
```python
from pydantic import Field, validator

class BookCreate(BookBase):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    publication_year: int = Field(..., ge=1800, le=2024)
    language: str = Field(..., min_length=2, max_length=2)
    page_count: int = Field(..., gt=0)
    authors: list[int] = Field(..., min_items=1)
    categories: list[int] = Field(..., min_items=1)
    tags: list[int] = Field(..., min_items=1)

    @validator('language')
    def validate_language(cls, v):
        if v not in ['ru', 'en']:
            raise ValueError('Language must be either "ru" or "en"')
        return v
```
