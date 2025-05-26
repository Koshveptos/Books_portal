"""
Модульные тесты для моделей базы данных
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Импортируем все модели из book.py
from app.models.book import Author, Book, Category, Language, Tag
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def get_test_moderator(async_session: AsyncSession) -> User:
    """Получение существующего модератора"""
    result = await async_session.execute(select(User).where(User.email == "test@example.com"))
    moderator = result.scalar_one_or_none()
    assert moderator is not None, "Тестовый модератор не найден"
    return moderator


async def test_create_user(async_session: AsyncSession):
    """Тест создания пользователя"""
    # Генерируем уникальный email
    unique_email = f"test_model_{uuid.uuid4().hex[:8]}@example.com"

    user = User(
        email=unique_email, hashed_password="hashed_password", is_active=True, is_superuser=False, is_moderator=False
    )

    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    assert user.id is not None
    assert user.email == unique_email
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.is_moderator is False

    # Удаляем тестового пользователя
    await async_session.delete(user)
    await async_session.commit()


@pytest.mark.asyncio
async def test_create_book(async_session: AsyncSession):
    """Тест создания книги"""
    # Получаем существующего модератора
    moderator = await get_test_moderator(async_session)
    assert moderator is not None, "Модератор не найден"
    assert moderator.is_moderator is True, "Пользователь должен быть модератором"

    # Создаем автора с уникальным именем
    author_name = f"Test Author {uuid.uuid4().hex[:8]}"
    author = Author(name=author_name)
    async_session.add(author)
    await async_session.commit()
    await async_session.refresh(author)

    # Создаем книгу с уникальным ISBN
    unique_isbn = f"978-3-16-148410-{uuid.uuid4().hex[:1]}"
    book = Book(
        title="Test Book Model",
        description="Test book description",
        year="2024",
        language=Language.RU,
        isbn=unique_isbn,
        file_url="test_url",
    )

    # Добавляем автора к книге через отношение
    book.authors.append(author)
    async_session.add(book)
    await async_session.commit()

    # Получаем книгу с авторами в отдельном запросе
    stmt = select(Book).options(selectinload(Book.authors)).where(Book.id == book.id)
    result = await async_session.execute(stmt)
    book_with_authors = result.scalar_one_or_none()

    assert book_with_authors is not None
    assert book_with_authors.title == "Test Book Model"
    assert book_with_authors.year == "2024"
    assert book_with_authors.language == Language.RU
    assert len(book_with_authors.authors) == 1
    assert book_with_authors.authors[0].name == author_name

    # Очищаем тестовые данные
    await async_session.delete(book)
    await async_session.delete(author)
    await async_session.commit()


@pytest.mark.asyncio
async def test_book_category_relationships(async_session: AsyncSession):
    """Тест связей книги с категориями"""
    # Создаем категорию
    category = Category(name="Test Category")
    async_session.add(category)
    await async_session.commit()


@pytest.mark.asyncio
async def test_book_tag_relationships(async_session: AsyncSession):
    """Тест связей книги с тегами"""
    # Создаем тег
    tag = Tag(name="Test Tag")
    async_session.add(tag)
    await async_session.commit()


@pytest.mark.asyncio
async def test_user_validation(async_session: AsyncSession):
    """Тест валидации пользователя"""
    # Проверяем существование модератора
    moderator = await get_test_moderator(async_session)
    assert moderator.email == "test@example.com"
    assert moderator.is_moderator is True
    assert moderator.is_active is True
