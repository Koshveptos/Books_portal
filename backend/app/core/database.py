## переписать все веремное

import logging

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logger_config import logger

# Определяем базовый класс для всех моделей если его нет
Base = declarative_base()


# Настройка логгера SQLAlchemy
class SQLAlchemyLogHandler(logging.Handler):
    def emit(self, record):
        message = self.format(record)
        logger.debug(f"SQLAlchemy: {message}")


sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
sqlalchemy_logger.setLevel(logging.INFO)
sqlalchemy_logger.addHandler(SQLAlchemyLogHandler())


# Функция для проверки подключения к БД
async def check_database_connection():
    logger.info(f"Connecting to database at {settings.DATABASE_URL}...")
    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO_LOG,
            future=True,
        )
        # Проверка подключения
        async with engine.connect():
            logger.info("Database connection successful")
        await engine.dispose()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False


# Создание движка базы данных
async def create_db_engine():
    logger.info(f"Connecting to database at {settings.DATABASE_URL}...")
    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO_LOG,
            future=True,
        )
        # Проверка подключения
        async with engine.connect():
            logger.success("Database connection established successfully.")
        return engine
    except OperationalError as e:
        logger.error(f"Failed to connect to the database: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database connection: {e}")
        raise


# Инициализация базы данных
async def init_db(engine: AsyncEngine):
    logger.info("Initializing database...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.success("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raise


# Dependency to get database session
async def get_db():
    logger.debug("Creating new database session...")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            logger.debug("Database session closed successfully.")
        except Exception as e:
            logger.error(f"Error in database session: {e}")
            raise


# Создание движка и сессии
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO_LOG,
    future=True,
)

# Создаем асинхронную сессию
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
