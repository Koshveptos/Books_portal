import asyncio
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base

# Настройка тестовой базы данных
TEST_DATABASE_URL = settings.TEST_DATABASE_URL

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
    pool_size=5,
    max_overflow=10,
)

TestingSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Создает новый event loop для тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Создает тестовую базу данных и сессию"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def client(db: AsyncSession) -> Generator:
    """Создает тестовый клиент с переопределенной зависимостью базы данных"""

    async def override_get_db():
        try:
            yield db
        finally:
            await db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(db: AsyncSession):
    """Создает тестового пользователя"""
    from app.core.auth import get_password_hash
    from app.models.user import User

    user = User(email="test@example.com", hashed_password=get_password_hash("testpassword123"), is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture(scope="function")
async def test_book(db: AsyncSession):
    """Создает тестовую книгу"""
    from app.models.book import Book

    book = Book(
        title="Test Book", isbn="1234567890123", description="Test Description", language="ru", file_url="test.pdf"
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book
