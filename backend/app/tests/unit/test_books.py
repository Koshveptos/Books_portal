"""
Модульные тесты для книг
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.book import Language

pytestmark = pytest.mark.asyncio


async def test_create_book(async_client: AsyncClient, async_session: AsyncSession, auth_headers: dict):
    """Тест создания книги"""
    # Создаем автора
    author_data = {"name": f"Test Author {uuid.uuid4().hex[:8]}"}
    author_response = await async_client.post("/authors/", json=author_data, headers=auth_headers)
    assert author_response.status_code == 201
    author_id = author_response.json()["id"]

    # Создаем категорию
    category_data = {"name_categories": f"Fiction_{uuid.uuid4().hex[:8]}"}
    category_response = await async_client.post("/categories/", json=category_data, headers=auth_headers)
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    # Создаем тег
    tag_data = {"name_tag": f"test_{uuid.uuid4().hex[:8]}"}
    tag_response = await async_client.post("/tags/", json=tag_data, headers=auth_headers)
    assert tag_response.status_code == 201
    tag_id = tag_response.json()["id"]

    # Создаем книгу
    book_data = {
        "title": "Test Book",
        "description": "Test book description",
        "year": "2024",
        "language": Language.RU,
        "isbn": f"978-3-16-148410-{uuid.uuid4().hex[:1]}",
        "file_url": "test_url",
        "authors": [author_id],
        "categories": [category_id],
        "tags": [tag_id],
    }

    response = await async_client.post("/books/", json=book_data, headers=auth_headers)
    assert response.status_code in (200, 201)
    assert "id" in response.json()


async def test_get_book(async_client: AsyncClient, async_session: AsyncSession, auth_headers: dict):
    """Тест получения книги"""
    # Создаем книгу для теста
    author_data = {"name": f"Test Author {uuid.uuid4().hex[:8]}"}
    author_response = await async_client.post("/authors/", json=author_data, headers=auth_headers)
    assert author_response.status_code == 201
    author_id = author_response.json()["id"]

    book_data = {
        "title": "Test Book for Get",
        "description": "Test book description",
        "year": "2024",
        "language": Language.RU,
        "isbn": f"978-3-16-148410-{uuid.uuid4().hex[:1]}",
        "file_url": "test_url",
        "authors": [author_id],
    }

    create_response = await async_client.post("/books/", json=book_data, headers=auth_headers)
    assert create_response.status_code in (200, 201)
    book_id = create_response.json()["id"]

    # Получаем книгу
    response = await async_client.get(f"/books/{book_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == book_id
    assert response.json()["title"] == book_data["title"]


async def test_update_book(async_client: AsyncClient, async_session: AsyncSession, auth_headers: dict):
    """Тест обновления книги"""
    # Создаем книгу для теста
    author_data = {"name": f"Test Author {uuid.uuid4().hex[:8]}"}
    author_response = await async_client.post("/authors/", json=author_data, headers=auth_headers)
    assert author_response.status_code == 201
    author_id = author_response.json()["id"]

    book_data = {
        "title": "Test Book for Update",
        "description": "Test book description",
        "year": "2024",
        "language": Language.RU,
        "isbn": f"978-3-16-148410-{uuid.uuid4().hex[:1]}",
        "file_url": "test_url",
        "authors": [author_id],
    }

    create_response = await async_client.post("/books/", json=book_data, headers=auth_headers)
    assert create_response.status_code in (200, 201)
    book_id = create_response.json()["id"]

    # Обновляем книгу
    update_data = {
        "title": "Updated Test Book",
        "description": "Updated test book description",
        "language": Language.EN,
    }

    response = await async_client.patch(f"/books/{book_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["title"] == update_data["title"]
    assert response.json()["description"] == update_data["description"]
    assert response.json()["language"] == update_data["language"]


async def test_delete_book(async_client: AsyncClient, async_session: AsyncSession, auth_headers: dict):
    """Тест удаления книги"""
    # Создаем книгу для теста
    author_data = {"name": f"Test Author {uuid.uuid4().hex[:8]}"}
    author_response = await async_client.post("/authors/", json=author_data, headers=auth_headers)
    assert author_response.status_code == 201
    author_id = author_response.json()["id"]

    book_data = {
        "title": "Test Book for Delete",
        "description": "Test book description",
        "year": "2024",
        "language": Language.RU,
        "isbn": f"978-3-16-148410-{uuid.uuid4().hex[:1]}",
        "file_url": "test_url",
        "authors": [author_id],
    }

    create_response = await async_client.post("/books/", json=book_data, headers=auth_headers)
    assert create_response.status_code in (200, 201)
    book_id = create_response.json()["id"]

    # Удаляем книгу
    response = await async_client.delete(f"/books/{book_id}", headers=auth_headers)
    assert response.status_code == 204

    # Проверяем, что книга удалена
    get_response = await async_client.get(f"/books/{book_id}", headers=auth_headers)
    assert get_response.status_code == 404


async def test_list_books(async_client: AsyncClient, async_session: AsyncSession, auth_headers: dict):
    """Тест получения списка книг"""
    # Создаем несколько книг для теста
    author_data = {"name": f"Test Author {uuid.uuid4().hex[:8]}"}
    author_response = await async_client.post("/authors/", json=author_data, headers=auth_headers)
    assert author_response.status_code == 201
    author_id = author_response.json()["id"]

    for i in range(3):
        book_data = {
            "title": f"Test Book {i}",
            "description": f"Test book description {i}",
            "year": "2024",
            "language": Language.RU,
            "isbn": f"978-3-16-148410-{uuid.uuid4().hex[:1]}",
            "file_url": "test_url",
            "authors": [author_id],
        }
        response = await async_client.post("/books/", json=book_data, headers=auth_headers)
        assert response.status_code in (200, 201)

    # Получаем список книг
    response = await async_client.get("/books/", headers=auth_headers)
    assert response.status_code == 200
    books = response.json()
    assert isinstance(books, list)
    assert len(books) >= 3
    assert all("id" in book for book in books)
    assert all("title" in book for book in books)
    assert all("authors" in book for book in books)
