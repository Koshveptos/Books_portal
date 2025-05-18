# Core Module

## Описание
Модуль содержит основные настройки и конфигурации приложения.

## Компоненты

### config.py
Конфигурация приложения, включающая:
- Настройки базы данных
- Настройки JWT
- Настройки Redis
- Настройки логирования
- Настройки CORS
- Настройки безопасности

### database.py
Настройки и подключение к базе данных:
- Создание сессии базы данных
- Настройка пула соединений
- Асинхронные операции с базой данных
- Миграции базы данных

### security.py
Функции безопасности:
- Хеширование паролей
- Генерация JWT токенов
- Проверка JWT токенов
- Проверка прав доступа
- Валидация данных

### exceptions.py
Пользовательские исключения:
- `BookNotFoundException` - книга не найдена
- `AuthorNotFoundException` - автор не найден
- `CategoryNotFoundException` - категория не найдена
- `TagNotFoundException` - тег не найден
- `UserNotFoundException` - пользователь не найден
- `InvalidCredentialsException` - неверные учетные данные
- `PermissionDeniedException` - недостаточно прав
- `ValidationException` - ошибка валидации данных

### logger_config.py
Настройки логирования:
- Форматирование логов
- Уровни логирования
- Ротация логов
- Отправка логов в файл и консоль

## Использование

### Конфигурация
```python
from app.core.config import settings

# Использование настроек
database_url = settings.DATABASE_URL
jwt_secret = settings.SECRET_KEY
```

### База данных
```python
from app.core.database import get_db

# Получение сессии базы данных
async with get_db() as db:
    # Работа с базой данных
    result = await db.execute(query)
```

### Безопасность
```python
from app.core.security import get_password_hash, verify_password

# Хеширование пароля
hashed_password = get_password_hash(password)

# Проверка пароля
is_valid = verify_password(password, hashed_password)
```

### Исключения
```python
from app.core.exceptions import BookNotFoundException

# Использование исключений
if not book:
    raise BookNotFoundException(book_id)
```

### Логирование
```python
from app.core.logger_config import logger

# Логирование
logger.info("Операция выполнена успешно")
logger.error("Произошла ошибка", exc_info=True)
```
