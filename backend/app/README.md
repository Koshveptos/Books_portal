# Books Portal Backend Application

## Структура приложения

### API (`api/`)
- `main.py` - Основной файл приложения
- `dependencies.py` - Зависимости FastAPI
- `auth.py` - Аутентификация и авторизация

### Core (`core/`)
- `config.py` - Конфигурация приложения
- `database.py` - Настройки базы данных
- `security.py` - Функции безопасности
- `exceptions.py` - Пользовательские исключения
- `logger_config.py` - Настройки логирования

### Models (`models/`)
- `book.py` - Модели для книг, авторов, категорий и тегов
- `user.py` - Модель пользователя
- `rating.py` - Модель рейтинга

### Schemas (`schemas/`)
- `book.py` - Pydantic схемы для книг
- `user.py` - Pydantic схемы для пользователей
- `rating.py` - Pydantic схемы для рейтингов

### Services (`services/`)
- `book_service.py` - Сервис для работы с книгами
- `user_service.py` - Сервис для работы с пользователями
- `rating_service.py` - Сервис для работы с рейтингами
- `recommendation_service.py` - Сервис рекомендаций

### Routers (`routers/`)
- `books.py` - Роуты для книг
- `users.py` - Роуты для пользователей
- `auth.py` - Роуты для аутентификации
- `categories.py` - Роуты для категорий
- `authors.py` - Роуты для авторов
- `tags.py` - Роуты для тегов
- `search.py` - Роуты для поиска
- `recommendations.py` - Роуты для рекомендаций
- `favorites.py` - Роуты для избранного
- `likes.py` - Роуты для лайков

### Utils (`utils/`)
- `validators.py` - Валидаторы данных
- `helpers.py` - Вспомогательные функции

### Tests (`tests/`)
- `test_auth.py` - Тесты аутентификации
- `test_book_auth.py` - Тесты авторизации для книг
- `test_jwt_auth.py` - Тесты JWT аутентификации
- `create_test_user.py` - Скрипт создания тестового пользователя

## Основные функции

### Аутентификация и авторизация
- Регистрация пользователей
- Вход в систему
- Обновление токена
- Проверка прав доступа

### Управление книгами
- Создание, чтение, обновление и удаление книг
- Поиск книг
- Фильтрация по категориям, авторам и тегам
- Сортировка по популярности и дате

### Управление пользователями
- Создание и обновление профиля
- Управление избранным
- Управление лайками
- Просмотр истории

### Рекомендации
- Персонализированные рекомендации
- Рекомендации по авторам
- Рекомендации по категориям
- Рекомендации по тегам

## API Endpoints

### Книги
- `GET /books/` - Получить список книг
- `GET /books/{book_id}` - Получить книгу по ID
- `POST /books/` - Создать книгу
- `PUT /books/{book_id}` - Обновить книгу
- `DELETE /books/{book_id}` - Удалить книгу
- `GET /books/category/{category_id}` - Получить книги по категории
- `GET /books/author/{author_id}` - Получить книги по автору
- `GET /books/tag/{tag_id}` - Получить книги по тегу

### Пользователи
- `POST /auth/register` - Регистрация
- `POST /auth/token` - Получение токена
- `GET /users/me` - Получить профиль
- `PUT /users/me` - Обновить профиль

### Поиск
- `GET /search/` - Поиск книг
- `GET /search/by-author` - Поиск по автору
- `GET /search/field/{field_name}` - Поиск по полю
- `GET /search/advanced` - Расширенный поиск

### Рекомендации
- `GET /recommendations/` - Получить рекомендации
- `GET /recommendations/by-author` - Рекомендации по авторам
- `GET /recommendations/by-category` - Рекомендации по категориям

### Избранное и лайки
- `GET /favorites/` - Получить избранные книги
- `POST /favorites/{book_id}` - Добавить в избранное
- `DELETE /favorites/{book_id}` - Удалить из избранного
- `GET /likes/` - Получить лайкнутые книги
- `POST /likes/{book_id}` - Лайкнуть книгу
- `DELETE /likes/{book_id}` - Убрать лайк
