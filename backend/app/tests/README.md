# Tests Module

## Описание
Модуль содержит тесты для проверки функциональности приложения.

## Тесты

### test_auth.py
Тесты для проверки аутентификации:

```python
def test_login_success(client: TestClient):
    """
    Проверка успешной аутентификации
    """
    pass

def test_login_invalid_credentials(client: TestClient):
    """
    Проверка аутентификации с неверными учетными данными
    """
    pass

def test_refresh_token(client: TestClient):
    """
    Проверка обновления токена
    """
    pass
```

### test_books.py
Тесты для проверки работы с книгами:

```python
def test_get_books(client: TestClient):
    """
    Проверка получения списка книг
    """
    pass

def test_get_book(client: TestClient):
    """
    Проверка получения книги по ID
    """
    pass

def test_create_book(client: TestClient, auth_headers: dict):
    """
    Проверка создания книги
    """
    pass

def test_update_book(client: TestClient, auth_headers: dict):
    """
    Проверка обновления книги
    """
    pass

def test_delete_book(client: TestClient, auth_headers: dict):
    """
    Проверка удаления книги
    """
    pass
```

### test_users.py
Тесты для проверки работы с пользователями:

```python
def test_create_user(client: TestClient):
    """
    Проверка создания пользователя
    """
    pass

def test_get_current_user(client: TestClient, auth_headers: dict):
    """
    Проверка получения информации о текущем пользователе
    """
    pass

def test_update_user(client: TestClient, auth_headers: dict):
    """
    Проверка обновления пользователя
    """
    pass

def test_delete_user(client: TestClient, auth_headers: dict):
    """
    Проверка удаления пользователя
    """
    pass
```

### test_recommendations.py
Тесты для проверки работы с рекомендациями:

```python
def test_get_recommendations(client: TestClient, auth_headers: dict):
    """
    Проверка получения рекомендаций
    """
    pass

def test_get_similar_users(client: TestClient, auth_headers: dict):
    """
    Проверка получения похожих пользователей
    """
    pass
```

## Фикстуры

### conftest.py
Общие фикстуры для тестов:

```python
@pytest.fixture
def client() -> TestClient:
    """
    Фикстура для создания тестового клиента
    """
    pass

@pytest.fixture
def db() -> Session:
    """
    Фикстура для создания тестовой сессии базы данных
    """
    pass

@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    """
    Фикстура для получения заголовков аутентификации
    """
    pass
```

## Использование

### Запуск тестов
```bash
# Запуск всех тестов
pytest

# Запуск конкретного теста
pytest tests/test_auth.py

# Запуск тестов с подробным выводом
pytest -v

# Запуск тестов с выводом print
pytest -s
```

### Пример теста
```python
def test_create_book(client: TestClient, auth_headers: dict):
    # Подготовка данных
    book_data = {
        "title": "Test Book",
        "description": "Test Description",
        "publication_year": 2023,
        "language": "ru",
        "page_count": 300,
        "authors": [1],
        "categories": [1],
        "tags": [1]
    }

    # Отправка запроса
    response = client.post(
        "/api/v1/books/",
        json=book_data,
        headers=auth_headers
    )

    # Проверка ответа
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == book_data["title"]
    assert data["description"] == book_data["description"]
```

### Пример использования фикстур
```python
def test_get_books(client: TestClient, db: Session):
    # Подготовка данных
    book = Book(
        title="Test Book",
        description="Test Description",
        publication_year=2023,
        language="ru",
        page_count=300
    )
    db.add(book)
    db.commit()

    # Отправка запроса
    response = client.get("/api/v1/books/")

    # Проверка ответа
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == book.title
```
