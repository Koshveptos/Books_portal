# Utils Module

## Описание
Модуль содержит вспомогательные функции и утилиты для работы приложения.

## Утилиты

### pagination.py
Функции для работы с пагинацией:

```python
def get_pagination_params(
    skip: int = 0,
    limit: int = 10,
    max_limit: int = 100
) -> Tuple[int, int]:
    """
    Получение параметров пагинации
    """
    pass

def get_pagination_response(
    items: List[Any],
    total: int,
    skip: int,
    limit: int
) -> Dict[str, Any]:
    """
    Формирование ответа с пагинацией
    """
    pass
```

### validation.py
Функции для валидации данных:

```python
def validate_email(email: str) -> bool:
    """
    Валидация email адреса
    """
    pass

def validate_password(password: str) -> bool:
    """
    Валидация пароля
    """
    pass

def validate_book_data(book_data: Dict[str, Any]) -> bool:
    """
    Валидация данных книги
    """
    pass
```

### cache.py
Функции для работы с кешированием:

```python
async def get_cached_data(
    redis_client: Redis,
    key: str,
    ttl: int = 3600
) -> Optional[Any]:
    """
    Получение данных из кеша
    """
    pass

async def set_cached_data(
    redis_client: Redis,
    key: str,
    value: Any,
    ttl: int = 3600
) -> None:
    """
    Сохранение данных в кеш
    """
    pass

async def invalidate_cache(
    redis_client: Redis,
    pattern: str
) -> None:
    """
    Инвалидация кеша по паттерну
    """
    pass
```

### logging.py
Функции для работы с логированием:

```python
def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None
) -> None:
    """
    Настройка логирования
    """
    pass

def get_logger(name: str) -> Logger:
    """
    Получение логгера
    """
    pass

def log_request(
    logger: Logger,
    request: Request,
    response: Response,
    duration: float
) -> None:
    """
    Логирование HTTP-запроса
    """
    pass
```

## Использование

### Пример работы с пагинацией
```python
from app.utils.pagination import get_pagination_params, get_pagination_response

# Получение параметров пагинации
skip, limit = get_pagination_params(skip=0, limit=20)

# Формирование ответа с пагинацией
response = get_pagination_response(
    items=books,
    total=total_books,
    skip=skip,
    limit=limit
)
```

### Пример работы с валидацией
```python
from app.utils.validation import validate_email, validate_password

# Валидация email
is_valid_email = validate_email("user@example.com")

# Валидация пароля
is_valid_password = validate_password("password123")
```

### Пример работы с кешированием
```python
from app.utils.cache import get_cached_data, set_cached_data

# Получение данных из кеша
cached_books = await get_cached_data(redis_client, "books:list")

# Сохранение данных в кеш
await set_cached_data(redis_client, "books:list", books)
```

### Пример работы с логированием
```python
from app.utils.logging import setup_logging, get_logger

# Настройка логирования
setup_logging(log_level="DEBUG", log_file="app.log")

# Получение логгера
logger = get_logger(__name__)

# Логирование
logger.info("Application started")
logger.error("Error occurred", exc_info=True)
```
