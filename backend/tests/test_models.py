import pytest
from sqlalchemy.exc import IntegrityError

from app.core.auth import get_password_hash
from app.models.book import Book
from app.models.rating import Rating
from app.models.user import User


@pytest.mark.asyncio
async def test_create_user(db):
    user = User(email="test@example.com", hashed_password=get_password_hash("testpassword123"), is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    assert user.email == "test@example.com"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_create_book(db):
    book = Book(
        title="Test Book", isbn="1234567890123", description="Test Description", language="ru", file_url="test.pdf"
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)

    assert book.title == "Test Book"
    assert book.isbn == "1234567890123"
    assert book.language == "ru"


@pytest.mark.asyncio
async def test_create_rating(db):
    # Создаем пользователя
    user = User(email="reviewer@example.com", hashed_password=get_password_hash("testpassword123"), is_active=True)
    db.add(user)
    await db.commit()

    # Создаем книгу
    book = Book(
        title="Test Book", isbn="1234567890123", description="Test Description", language="ru", file_url="test.pdf"
    )
    db.add(book)
    await db.commit()

    # Создаем рейтинг
    rating = Rating(user_id=user.id, book_id=book.id, rating=5, comment="Great book!")
    db.add(rating)
    await db.commit()
    await db.refresh(rating)

    assert rating.rating == 5
    assert rating.comment == "Great book!"
    assert rating.user_id == user.id
    assert rating.book_id == book.id


@pytest.mark.asyncio
async def test_unique_email_constraint(db):
    # Создаем первого пользователя
    user1 = User(email="unique@example.com", hashed_password=get_password_hash("testpassword123"), is_active=True)
    db.add(user1)
    await db.commit()

    # Пытаемся создать второго пользователя с тем же email
    user2 = User(email="unique@example.com", hashed_password=get_password_hash("anotherpassword"), is_active=True)
    db.add(user2)

    with pytest.raises(IntegrityError):
        await db.commit()
