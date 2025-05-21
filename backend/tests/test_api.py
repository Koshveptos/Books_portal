import pytest
from fastapi import status

from tests.utils import create_test_token


@pytest.mark.asyncio
async def test_register_user(client):
    response = client.post("/auth/register", json={"email": "newuser@example.com", "password": "testpassword123"})
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "password" not in data


@pytest.mark.asyncio
async def test_login_user(client, db):
    # Сначала регистрируем пользователя
    client.post("/auth/register", json={"email": "loginuser@example.com", "password": "testpassword123"})

    # Пытаемся войти
    response = client.post("/auth/jwt/login", data={"username": "loginuser@example.com", "password": "testpassword123"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_create_book(client, db, test_user):
    # Создаем токен для авторизованного пользователя
    access_token = create_test_token({"sub": test_user.email})

    response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "title": "New Book",
            "isbn": "1234567890123",
            "description": "Test Description",
            "language": "ru",
            "file_url": "test.pdf",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "New Book"
    assert data["isbn"] == "1234567890123"


@pytest.mark.asyncio
async def test_get_books(client, db):
    response = client.get("/books/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_book_by_id(client, db, test_user):
    # Сначала создаем книгу
    access_token = create_test_token({"sub": test_user.email})
    create_response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "title": "Test Book",
            "isbn": "1234567890123",
            "description": "Test Description",
            "language": "ru",
            "file_url": "test.pdf",
        },
    )
    book_id = create_response.json()["id"]

    # Получаем книгу по ID
    response = client.get(f"/books/{book_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == book_id
    assert data["title"] == "Test Book"


@pytest.mark.asyncio
async def test_create_rating(client, db, test_user):
    # Создаем токен для авторизованного пользователя
    access_token = create_test_token({"sub": test_user.email})

    # Сначала создаем книгу
    create_response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "title": "Test Book",
            "isbn": "1234567890123",
            "description": "Test Description",
            "language": "ru",
            "file_url": "test.pdf",
        },
    )
    book_id = create_response.json()["id"]

    # Создаем рейтинг
    response = client.post(
        f"/books/{book_id}/ratings",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"rating": 5, "comment": "Great book!"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["rating"] == 5
    assert data["comment"] == "Great book!"
