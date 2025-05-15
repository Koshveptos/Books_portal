import os

# Добавляем путь к приложению в sys.path для абсолютных импортов
import sys
import time
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

# Исправлен импорт - в директории core файл конфигурации называется config, а не settings
from core.config import settings
from core.exceptions import BookPortalException
from core.logger_config import logger
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Правильные импорты из 'routers' вместо 'routes'
from routers.auth import router as auth_router
from routers.authors import router as authors_router
from routers.books import books_router as flat_books_router  # Импортируем плоский роутер для книг
from routers.books import router as books_router
from routers.categories import router as categories_router
from routers.favorites import router as favorites_router
from routers.likes import router as likes_router
from routers.ratings import router as ratings_router
from routers.recommendations import router as recommendations_router
from routers.search import router as search_router
from routers.tags import router as tags_router
from routers.user import router as users_router

# from starlette.requests import Request

# потом все подключения роутеров в один файл перекинуть и там настроить все


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    yield
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
app.include_router(books_router, prefix="/books", tags=["books"])
app.include_router(flat_books_router, prefix="/books", tags=["flat_books"])  # Добавляем плоский роутер
app.include_router(authors_router, prefix="/authors", tags=["authors"])
app.include_router(categories_router, prefix="/categories", tags=["categories"])
app.include_router(tags_router, prefix="/tags", tags=["tags"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(auth_router)
app.include_router(search_router, prefix="/search", tags=["search"])
app.include_router(recommendations_router)
app.include_router(likes_router)
app.include_router(favorites_router)
app.include_router(ratings_router)


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
    logger.warning(
        f"BookPortalException: {exc.error_code} - {exc.message} - " f"URL: {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


# Обработчик ошибок валидации Pydantic
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = []

    for error in errors:
        error_messages.append({"loc": error.get("loc", []), "msg": error.get("msg", ""), "type": error.get("type", "")})

    logger.warning(f"Validation error for {request.method} {request.url.path}: {errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error_code": "validation_error", "message": "Ошибка валидации данных", "details": error_messages},
    )


# Общий обработчик непредвиденных ошибок (500)
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(
        f"Unhandled exception for {request.method} {request.url.path}. "
        f"Headers: {request.headers}, Query: {request.query_params}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error_code": "internal_error", "message": "Внутренняя ошибка сервера"},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000, log_level="debug")
