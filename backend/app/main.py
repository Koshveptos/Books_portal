import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from core.config import settings
from core.database import init_db
from core.dependencies import init_redis
from core.exceptions import (
    BookPortalException,
)
from core.logger_config import (
    log_business_error,
    log_db_error,
    log_performance,
    log_validation_error,
    logger,
)
from core.middleware import setup_middleware

# Импорты роутеров
from routers.auth import router as auth_router
from routers.authors import router as authors_router
from routers.books import books_router as flat_books_router
from routers.books import router as books_router
from routers.categories import router as categories_router
from routers.favorites import router as favorites_router
from routers.likes import router as likes_router
from routers.ratings import router as ratings_router
from routers.recommendations import router as recommendations_router
from routers.search import router as search_router
from routers.tags import router as tags_router
from routers.user import router as users_router

from bot.run_bot import start_bot, stop_bot

# Настройка логгера
logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Контекстный менеджер для управления жизненным циклом приложения"""
    start_time = time.time()
    logger.info("Запуск приложения...")

    # Список задач для очистки
    cleanup_tasks = []

    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        await init_db()
        logger.info("Database initialized successfully")

        # Инициализация Redis
        logger.info("Инициализация Redis...")
        try:
            await init_redis()
            logger.info("Redis initialized successfully")
        except Exception as e:
            logger.error(
                "Ошибка инициализации Redis", extra={"error": str(e), "error_type": type(e).__name__}, exc_info=True
            )
            logger.warning("Приложение будет работать без Redis")

        # Запуск Telegram бота
        logger.info("Запуск Telegram бота...")
        bot_task = asyncio.create_task(start_bot())
        cleanup_tasks.append(bot_task)
        logger.info("Telegram bot started successfully")

        yield

        # Остановка всех задач
        logger.info("Остановка приложения...")
        for task in cleanup_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Остановка Telegram бота
        await stop_bot()
        logger.info("Telegram bot stopped successfully")

    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске приложения: {str(e)}", exc_info=True)
        raise
    finally:
        duration = time.time() - start_time
        log_performance("application_lifespan", duration)
        logger.info("Завершение работы приложения...")


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API для управления книжным порталом с рекомендациями",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Настраиваем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Настройка middleware
setup_middleware(app)

# Подключаем роутеры
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(books_router, prefix="/books", tags=["books"])
app.include_router(flat_books_router, prefix="/books", tags=["flat_books"])
app.include_router(authors_router, prefix="/authors", tags=["authors"])
app.include_router(categories_router, prefix="/categories", tags=["categories"])
app.include_router(tags_router, prefix="/tags", tags=["tags"])
app.include_router(search_router, prefix="/search", tags=["search"])
app.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])
app.include_router(likes_router, prefix="/likes", tags=["likes"])
app.include_router(favorites_router, prefix="/favorites", tags=["favorites"])
app.include_router(ratings_router, prefix="/ratings", tags=["ratings"])

logger.info("Все роутеры успешно подключены")


@app.get("/")
async def root():
    """Корневой эндпоинт для проверки работоспособности API"""
    logger.debug("Получен запрос к корневому эндпоинту")
    return {
        "message": "Welcome to Books Portal API",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/health")
async def health_check():
    """
    Эндпоинт для проверки здоровья приложения.
    """
    return {"status": "healthy", "version": settings.VERSION}


# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware для логирования всех HTTP запросов"""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", "-")

    # Логируем начало запроса
    logger.debug(
        f"[{request_id}] Начало запроса: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "Unknown",
            "user_agent": request.headers.get("user-agent", "Unknown"),
        },
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Формируем контекст для логирования
        log_context: Dict[str, Any] = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": process_time,
            "client": request.client.host if request.client else "Unknown",
        }

        # Логируем с разным уровнем в зависимости от статуса
        if response.status_code >= 500:
            logger.error(
                f"[{request_id}] Ошибка сервера: {request.method} {request.url.path} - "
                f"Статус: {response.status_code} - Время: {process_time:.4f}с",
                extra=log_context,
            )
        elif response.status_code >= 400:
            logger.warning(
                f"[{request_id}] Ошибка клиента: {request.method} {request.url.path} - "
                f"Статус: {response.status_code} - Время: {process_time:.4f}с",
                extra=log_context,
            )
        else:
            logger.info(
                f"[{request_id}] Успешный запрос: {request.method} {request.url.path} - "
                f"Статус: {response.status_code} - Время: {process_time:.4f}с",
                extra=log_context,
            )

        # Логируем производительность
        log_performance(f"http_request_{request.method}_{request.url.path}", process_time, log_context)

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.exception(
            f"[{request_id}] Необработанная ошибка: {request.method} {request.url.path} - "
            f"Время: {process_time:.4f}с",
            exc_info=True,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "process_time": process_time,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Внутренняя ошибка сервера"},
        )


# Обработчик пользовательских исключений
@app.exception_handler(BookPortalException)
async def book_portal_exception_handler(request: Request, exc: BookPortalException):
    """Обработчик исключений BookPortalException"""
    log_business_error(
        message=str(exc),
        context={
            "request_id": request.headers.get("X-Request-ID", "-"),
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# Обработчик ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации запросов"""
    log_validation_error(
        "request_validation_error",
        error=exc,
        context={
            "request_id": request.headers.get("X-Request-ID", "-"),
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


# Обработчик ошибок базы данных
@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Обработчик ошибок базы данных"""
    log_db_error(
        exc,
        operation="database_operation",
        context={
            "request_id": request.headers.get("X-Request-ID", "-"),
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Ошибка базы данных"},
    )


# Обработчик общих исключений
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик всех остальных исключений"""
    logger.exception(
        f"Необработанное исключение: {str(exc)}",
        exc_info=True,
        extra={
            "request_id": request.headers.get("X-Request-ID", "-"),
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера"},
    )


if __name__ == "__main__":
    logger.info("Starting Uvicorn server...")
    try:
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level="debug",  # Устанавливаем уровень логирования в debug
            access_log=True,  # Включаем логирование доступа
            workers=1,  # Используем один воркер для отладки
            loop="asyncio",  # Явно указываем использование asyncio
            timeout_keep_alive=30,  # Уменьшаем время ожидания keep-alive
        )
    except Exception as e:
        logger.critical(f"Failed to start Uvicorn server: {str(e)}", exc_info=True)
        raise
