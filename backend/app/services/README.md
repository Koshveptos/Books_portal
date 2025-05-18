# Services Module

## Описание
Модуль содержит сервисные классы для работы с бизнес-логикой приложения.

## Сервисы

### book_service.py
Сервис для работы с книгами:

#### BookService
```python
class BookService:
    def __init__(self, db: Session):
        self.db = db

    def get_books(
        self,
        skip: int = 0,
        limit: int = 10,
        category_id: Optional[int] = None,
        author_id: Optional[int] = None,
        tag_id: Optional[int] = None,
        sort_by: Optional[str] = None
    ) -> List[Book]:
        """
        Получение списка книг с фильтрацией и сортировкой
        """
        pass

    def get_book(self, book_id: int) -> Optional[Book]:
        """
        Получение книги по ID
        """
        pass

    def create_book(self, book_data: BookCreate) -> Book:
        """
        Создание новой книги
        """
        pass

    def update_book(self, book_id: int, book_data: BookUpdate) -> Optional[Book]:
        """
        Обновление книги
        """
        pass

    def delete_book(self, book_id: int) -> bool:
        """
        Удаление книги
        """
        pass
```

### user_service.py
Сервис для работы с пользователями:

#### UserService
```python
class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Получение пользователя по ID
        """
        pass

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Получение пользователя по email
        """
        pass

    def create_user(self, user_data: UserCreate) -> User:
        """
        Создание нового пользователя
        """
        pass

    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """
        Обновление пользователя
        """
        pass

    def delete_user(self, user_id: int) -> bool:
        """
        Удаление пользователя
        """
        pass
```

### auth_service.py
Сервис для работы с аутентификацией:

#### AuthService
```python
class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Аутентификация пользователя
        """
        pass

    def create_access_token(self, data: dict) -> str:
        """
        Создание JWT токена
        """
        pass

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Проверка JWT токена
        """
        pass
```

### recommendation_service.py
Сервис для работы с рекомендациями:

#### RecommendationService
```python
class RecommendationService:
    def __init__(self, db: Session, redis_client: Redis):
        self.db = db
        self.redis = redis_client

    def get_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        category_id: Optional[int] = None,
        author_id: Optional[int] = None
    ) -> List[Book]:
        """
        Получение рекомендаций для пользователя
        """
        pass

    def update_user_preferences(self, user_id: int, book_id: int, rating: float):
        """
        Обновление предпочтений пользователя
        """
        pass

    def get_similar_users(self, user_id: int, limit: int = 5) -> List[User]:
        """
        Получение похожих пользователей
        """
        pass
```

## Использование

### Пример работы с BookService
```python
from app.services.book_service import BookService
from app.schemas.book import BookCreate

# Создание сервиса
book_service = BookService(db_session)

# Получение списка книг
books = book_service.get_books(
    skip=0,
    limit=10,
    category_id=1,
    sort_by="rating"
)

# Создание книги
book_data = BookCreate(
    title="Новая книга",
    description="Описание",
    publication_year=2023,
    language="ru",
    page_count=300,
    authors=[1, 2],
    categories=[1],
    tags=[1, 2]
)
new_book = book_service.create_book(book_data)
```

### Пример работы с AuthService
```python
from app.services.auth_service import AuthService

# Создание сервиса
auth_service = AuthService(db_session)

# Аутентификация
user = auth_service.authenticate_user("user@example.com", "password")

# Создание токена
token_data = {"sub": user.email, "role": user.role}
token = auth_service.create_access_token(token_data)

# Проверка токена
payload = auth_service.verify_token(token)
```

### Пример работы с RecommendationService
```python
from app.services.recommendation_service import RecommendationService

# Создание сервиса
recommendation_service = RecommendationService(db_session, redis_client)

# Получение рекомендаций
recommendations = recommendation_service.get_recommendations(
    user_id=1,
    limit=5,
    category_id=1
)

# Обновление предпочтений
recommendation_service.update_user_preferences(
    user_id=1,
    book_id=1,
    rating=4.5
)

# Получение похожих пользователей
similar_users = recommendation_service.get_similar_users(
    user_id=1,
    limit=3
)
```
