import time
from contextlib import asynccontextmanager

import uvicorn
from core.logger_config import logger
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from routers.books import router as books_router
from routers.users import router as users_router

# потом все подключения роутеров в один файл перекинуть и там настроить все


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    yield
    logger.info("Application shutdown...")


app = FastAPI(lifespan=lifespan, title="Books Portal")

app.include_router(books_router, prefix="/books", tags=["books"])
app.include_router(users_router)


@app.get("/")
async def root():
    return {"message": "Welcome to the Books API"}


# Middleware для логирования каждого запроса
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.debug(f"Request started: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Took: {process_time:.4f}s"
        )
    except Exception as e:
        process_time = time.time() - start_time
        logger.exception(f"Request failed: {request.method} {request.url.path} - " f"Took: {process_time:.4f}s")
        raise e
    return response


# Обработчик ошибок валидации Pydantic
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    logger.warning(f"Validation error for {request.method} {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
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
        content={"detail": "Internal Server Error"},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000, log_level="debug")
