# 📚 Books Portal API

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Books Portal** — современный REST API, реализующий онлайн-библиотеку с категориями, тегами, системой рекомендаций и интеграцией с Telegram-ботом.

---

## 🔥 Особенности

- 📚 CRUD API для управления книгами
- 🏷️ Поддержка категорий и тегов
- 🧠 Рекомендательная система
- 🔐 JWT-аутентификация
- 🧾 Документация (Swagger / Redoc)
- 🐳 Docker-контейнеризация
- 🔄 Миграции с помощью Alembic
- 🧪 Тестирование с Pytest и unittest
- 🤖 Интеграция с Telegram-ботом
- 📊 Рейтинги и отзывы
- 📈 Логирование (Loguru)
- 🔎 Пагинация и фильтрация

---

## 🛠️ Технологический стек

- **Язык**: Python 3.11+
- **Фреймворк**: FastAPI
- **БД**: PostgreSQL
- **ORM**: SQLAlchemy 2.0
- **Аутентификация**: JWT
- **Валидация**: Pydantic v2
- **Документация**: Swagger / Redoc
- **Управление зависимостями**: Poetry
- **Контейнеризация**: Docker, Docker Compose
- **Логирование**: Loguru
- **Тестирование**: Pytest, unittest

---

## 🚀 Быстрый старт

### 📋 Предварительные требования

- Docker Desktop

### ⚙️ Установка и запуск

1. Клонируйте репозиторий:

```bash
git clone https://github.com/Koshveptos/Books_portal.git
cd Books_portal
```

2. Создайте файл `backend/Dockerfile` со следующим содержимым:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Установка необходимых системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY app/ ./app/

# Установка poetry и замена psycopg2 на psycopg2-binary
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    sed -i 's/psycopg2 (>=2.9.10,<3.0.0)/psycopg2-binary (>=2.9.10,<3.0.0)/g' pyproject.toml && \
    poetry install

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

3. Создайте файл `docker-compose.yml` в корне проекта:

```yaml
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/books_db
    depends_on:
      - db

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=books_db
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

4. Запустите контейнеры:

```bash
docker compose up --build
```

Будут запущены:

- 🌐 API сервер: http://localhost:8000
- 🛢️ PostgreSQL: localhost:5432

5. В отдельном терминале примените миграции (если они созданы):

```bash
docker compose exec api alembic upgrade head
```

---

## 📚 Документация API

- Swagger UI: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

---

## 🌟 Основные эндпоинты

### 📘 Книги

| Метод | Путь                                | Описание                                |
|--------|--------------------------------------|------------------------------------------|
| GET    | /api/v1/books/                      | Получить список книг с пагинацией       |
| POST   | /api/v1/books/                      | Создать новую книгу (требуется авторизация) |
| GET    | /api/v1/books/{id}                  | Получить книгу по ID                    |
| PUT    | /api/v1/books/{id}                  | Полное обновление книги                 |
| PATCH  | /api/v1/books/{id}                  | Частичное обновление                    |
| DELETE | /api/v1/books/{id}                  | Удалить книгу                           |
| GET    | /api/v1/books/recommendations       | Получить рекомендации                   |

### 🔐 Аутентификация

| Метод | Путь                    | Описание                         |
|--------|--------------------------|----------------------------------|
| POST   | /api/v1/auth/login      | Получить JWT токен               |
| POST   | /api/v1/auth/register   | Регистрация нового пользователя  |
| GET    | /api/v1/auth/me         | Информация о текущем пользователе|

### 🤖 Telegram бот

| Метод | Путь                         | Описание                         |
|--------|-------------------------------|----------------------------------|
| POST   | /api/v1/telegram/webhook     | Webhook для Telegram бота        |

---

## 🏗️ Структура проекта

```bash
backend/
├── app/                  # Основное приложение
│   ├── routers/              # Роутеры API
│   ├── core/             # Основные настройки
│   ├── models/           # Модели БД
│   ├── schemas/          # Pydantic схемы
│   ├── services/         # Бизнес-логика
│   ├── utils/            # Вспомогательные утилиты
│   └── main.py           # Точка входа
├── migrations/           # Миграции Alembic
├── tests/                # Тесты
├── .env.example          # Пример env файла
├── alembic.ini           # Конфиг Alembic
├── docker-compose.yml    # Конфиг Docker
├── Dockerfile            # Конфиг Docker образа
└── pyproject.toml        # Конфиг Poetry
```

---

## 🛠 Режим разработки

### Установка зависимостей

```bash
poetry install
```

### Запуск в режиме разработки

```bash
uvicorn app.main:app --reload
```

### Создание и применение миграций

Создание новой миграции:

```bash
alembic revision --autogenerate -m "Описание изменений"
```

Применение миграций:

```bash
alembic upgrade head
```

---

## ✅ Тестирование

```bash
pytest
```

---

## 🎨 Линтинг и форматирование

```bash
flake8 .
black .
isort .
```

---

## 🤖 Интеграция с Telegram

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Укажите токен в `.env` файле:

```env
TELEGRAM_BOT_TOKEN=your_token_here
```

3. Установите webhook:

```bash
curl -X POST "http://localhost:8000/api/v1/telegram/set_webhook?url=https://your-domain.com/api/v1/telegram/webhook"
```

---

## 🐳 Docker команды

### Просмотр логов

```bash
docker compose logs -f api
```

### Остановка сервисов

```bash
docker compose down
```

### Полная очистка (включая данные базы)

```bash
docker compose down -v
```

### Доступ к базе данных

```bash
docker compose exec db psql -U postgres -d books_db
```

### Перезапуск только API сервера

```bash
docker compose restart api
```

---

## 📄 Лицензия

Распространяется под лицензией MIT. Подробнее см. в файле LICENSE.
