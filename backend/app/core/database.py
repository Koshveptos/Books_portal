"""
Модуль для работы с базой данных.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.exceptions import (
    DatabaseConnectionException,
    DatabaseInitializationException,
    DatabaseSessionException,
)
from app.core.logger_config import logger

# Определяем базовый класс для всех моделей
Base = declarative_base()


# Настройка логгера SQLAlchemy
class SQLAlchemyLogHandler(logging.Handler):
    """Обработчик логов для SQLAlchemy"""

    def emit(self, record):
        message = self.format(record)
        logger.debug(f"SQLAlchemy: {message}")


sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
sqlalchemy_logger.setLevel(logging.INFO)
sqlalchemy_logger.addHandler(SQLAlchemyLogHandler())


# Глобальные переменные
engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[sessionmaker] = None


async def check_database_connection() -> bool:
    """
    Проверяет подключение к базе данных.

    Returns:
        bool: True если подключение успешно, False в противном случае
    """
    start_time = time.time()
    logger.info(f"Проверка подключения к базе данных: {settings.DATABASE_URL}")

    try:
        temp_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO_LOG,
            future=True,
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
        )

        async with temp_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("Подключение к базе данных успешно установлено")

        await temp_engine.dispose()

        duration = time.time() - start_time
        logger.debug(
            "Database connection check completed", extra={"duration": duration, "database_url": settings.DATABASE_URL}
        )
        return True

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "Database connection check failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": duration,
                "database_url": settings.DATABASE_URL,
            },
            exc_info=True,
        )
        raise DatabaseConnectionException(f"Не удалось подключиться к базе данных: {str(e)}")


async def create_db_engine() -> AsyncEngine:
    """
    Создает и возвращает движок базы данных.

    Returns:
        AsyncEngine: Асинхронный движок SQLAlchemy
    """
    start_time = time.time()
    logger.info(f"Создание движка базы данных: {settings.DATABASE_URL}")

    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO_LOG,
            future=True,
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
        )

        # Проверка подключения
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("Движок базы данных успешно создан")

        duration = time.time() - start_time
        logger.debug("Database engine created", extra={"duration": duration, "database_url": settings.DATABASE_URL})
        return engine

    except OperationalError as e:
        duration = time.time() - start_time
        logger.error(
            "Database engine creation failed - operational error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": duration,
                "database_url": settings.DATABASE_URL,
            },
            exc_info=True,
        )
        raise DatabaseConnectionException(f"Не удалось подключиться к базе данных: {str(e)}")

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "Database engine creation failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": duration,
                "database_url": settings.DATABASE_URL,
            },
            exc_info=True,
        )
        raise DatabaseConnectionException(f"Ошибка при создании движка базы данных: {str(e)}")


async def init_db() -> None:
    """
    Инициализирует базу данных, создавая все таблицы.
    """
    global engine, AsyncSessionLocal

    start_time = time.time()
    logger.info("Инициализация базы данных...")

    try:
        # Создаем движок базы данных
        engine = await create_db_engine()

        # Создаем фабрику сессий
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
        )

        # Создаем таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("База данных успешно инициализирована")

        duration = time.time() - start_time
        logger.debug(
            "Database initialization completed", extra={"duration": duration, "database_url": settings.DATABASE_URL}
        )

    except SQLAlchemyError as e:
        duration = time.time() - start_time
        logger.error(
            "Database initialization failed - SQLAlchemy error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": duration,
                "database_url": settings.DATABASE_URL,
            },
            exc_info=True,
        )
        raise DatabaseInitializationException(f"Не удалось инициализировать базу данных: {str(e)}")

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "Database initialization failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": duration,
                "database_url": settings.DATABASE_URL,
            },
            exc_info=True,
        )
        raise DatabaseInitializationException(f"Ошибка при инициализации базы данных: {str(e)}")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Контекстный менеджер для работы с сессией базы данных.

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    global AsyncSessionLocal
    if not AsyncSessionLocal:
        # Попробуем инициализировать базу данных повторно
        logger.warning("AsyncSessionLocal не инициализирован, повторная инициализация базы данных!")
        await init_db()
        if not AsyncSessionLocal:
            raise DatabaseConnectionException("Движок базы данных не инициализирован")
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error("Database session error", extra={"error": str(e), "error_type": type(e).__name__}, exc_info=True)
        raise DatabaseSessionException(f"Ошибка в сессии базы данных: {str(e)}")
    except Exception as e:
        await session.rollback()
        logger.error(
            "Unexpected database session error", extra={"error": str(e), "error_type": type(e).__name__}, exc_info=True
        )
        raise DatabaseSessionException(f"Неожиданная ошибка в сессии базы данных: {str(e)}")
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI, предоставляющая сессию базы данных.

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    async with get_db_session() as session:
        yield session


async def close_db_connection() -> None:
    """
    Закрывает соединение с базой данных.
    """
    global engine

    if engine:
        try:
            await engine.dispose()
            logger.info("Соединение с базой данных успешно закрыто")
        except Exception as e:
            logger.error(
                "Failed to close database connection",
                extra={"error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            raise DatabaseConnectionException(f"Ошибка при закрытии соединения с базой данных: {str(e)}")
