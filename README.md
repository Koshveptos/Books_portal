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

- Docker и Docker Compose
- Python 3.11+
- Telegram Bot Token

### ⚙️ Установка и запуск

1. Клонируйте репозиторий:

```bash
git clone https://github.com/Koshveptos/Books_portal.git
cd Books_portal
## ⚙️ Установка и запуск

### 1. Скопируйте `.env` файл и настройте переменные


cp .env.example .env
# Отредактируйте .env файл под свою конфигурацию
```

### 2. Запустите контейнеры

```bash
docker-compose up -d --build
```

Будут запущены:

- 🌐 API сервер: http://localhost:8000
- 🛢️ PostgreSQL: localhost:5432
- 🧭 PgAdmin (опционально): localhost:5050

### 3. Примените миграции

```bash
docker-compose exec backend alembic upgrade head
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



## 📄 Лицензия

Распространяется под лицензией MIT. Подробнее см. в файле LICENSE.
