import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Добавляем путь к приложению в sys.path для абсолютных импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

from app.bot.run_bot import run_bot
from app.core.config import settings
from app.core.exceptions import BookPortalException
from app.core.logger_config import (
    log_business_error,
    log_critical_error,
    log_validation_error,
    log_warning,
)

# Настройка логгера
logger = logging.getLogger("books_portal")
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Контекстный менеджер для управления жизненным циклом приложения"""
    logger.info("Application startup...")
    # Запускаем бота в фоновом режиме
    bot_task = asyncio.create_task(run_bot())
    yield
    # Отменяем задачу бота при завершении работы приложения
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    logger.info("Application shutdown...")


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API для управления книжным порталом с рекомендациями",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Настраиваем CORS middleware для возможности запросов с фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене нужно ограничить список разрешенных источников
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Настраиваем и включаем все роутеры с правильными тегами
app.include_router(auth_router)  # Подключаем auth_router первым
app.include_router(users_router)  # Убираем prefix="/users", так как он уже есть в роутере
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


@app.get("/")
async def root():
    return {"message": "Welcome to the Books API"}


# Middleware для логирования каждого запроса
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", "-")
    logger.debug(f"[{request_id}] Request started: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        status_code = response.status_code
        log_message = (
            f"[{request_id}] Request completed: {request.method} {request.url.path} - "
            f"Status: {status_code} - Took: {process_time:.4f}s"
        )

        # Логгируем с разным уровнем в зависимости от статуса
        if status_code >= 500:
            logger.error(log_message)
        elif status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    except Exception as e:
        process_time = time.time() - start_time
        logger.exception(
            f"[{request_id}] Request failed: {request.method} {request.url.path} - "
            f"Took: {process_time:.4f}s - Error: {str(e)}"
        )
        raise e
    return response


# Обработчик наших пользовательских исключений
@app.exception_handler(BookPortalException)
async def book_portal_exception_handler(request: Request, exc: BookPortalException):
    """Обработчик исключений приложения"""
    log_business_error(
        error=exc,
        operation=request.url.path,
        context={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "Unknown",
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


# Обработчик ошибок валидации Pydantic
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = []

    for error in errors:
        error_messages.append(
            {
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
                "input": error.get("input", None),
            }
        )

    log_validation_error(
        exc,
        model_name=request.url.path.split("/")[-1],
        field=error_messages[0].get("loc", [])[-1] if error_messages else None,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "validation_error",
            "message": "Ошибка валидации данных",
            "details": error_messages,
            "path": request.url.path,
            "timestamp": time.time(),
        },
    )


# Обработчик ошибок 404 Not Found
@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_exception_handler(request: Request, exc: Exception):
    log_warning(
        f"Resource not found: {request.method} {request.url.path}",
        context={
            "client": request.client.host if request.client else "Unknown",
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "query_params": dict(request.query_params),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error_code": "not_found",
            "message": "Запрашиваемый ресурс не найден",
            "path": request.url.path,
            "timestamp": time.time(),
        },
    )


# Обработчик ошибок 405 Method Not Allowed
@app.exception_handler(status.HTTP_405_METHOD_NOT_ALLOWED)
async def method_not_allowed_exception_handler(request: Request, exc: Exception):
    log_warning(
        f"Method not allowed: {request.method} {request.url.path}",
        context={
            "client": request.client.host if request.client else "Unknown",
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "query_params": dict(request.query_params),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={
            "error_code": "method_not_allowed",
            "message": "Метод не разрешен",
            "path": request.url.path,
            "timestamp": time.time(),
        },
    )


# Обработчик ошибок 429 Too Many Requests
@app.exception_handler(status.HTTP_429_TOO_MANY_REQUESTS)
async def too_many_requests_exception_handler(request: Request, exc: Exception):
    log_warning(
        f"Too many requests: {request.method} {request.url.path}",
        context={
            "client": request.client.host if request.client else "Unknown",
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "query_params": dict(request.query_params),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error_code": "too_many_requests",
            "message": "Слишком много запросов",
            "path": request.url.path,
            "timestamp": time.time(),
        },
    )


# Общий обработчик непредвиденных ошибок (500)
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик необработанных исключений"""
    log_critical_error(
        error=exc,
        component="application",
        context={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "Unknown",
        },
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"},
    )


# Вывод всех маршрутов приложения для отладки
for route in app.routes:
    print(f"ROUTE: {route.path}")


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000, log_level="debug")
