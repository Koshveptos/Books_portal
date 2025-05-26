"""
Интеграционные тесты для API
"""

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.schemas.book import Language
from app.tests.conftest import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, test_stats

pytestmark = pytest.mark.asyncio


async def get_test_admin_token(async_client: AsyncClient) -> str:
    """Получение токена для тестового администратора"""
    login_data = {"username": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD}

    response = await async_client.post(
        "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200, f"Ошибка входа: {response.text}"
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_full_user_workflow(async_client: AsyncClient):
    """Тест полного цикла работы с пользователем"""
    test_stats["integration"]["total"] += 1
    try:
        # Регистрируем нового пользователя (без повышенных привилегий)
        user_data = {
            "email": f"test_user_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Test1234!",
            "is_active": True,
        }

        register_response = await async_client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201, f"Ошибка регистрации: {register_response.text}"
        user = register_response.json()

        # Проверяем, что пользователь создан без повышенных привилегий
        assert not user.get("is_moderator", False), "Пользователь не должен иметь прав модератора"
        assert not user.get("is_superuser", False), "Пользователь не должен иметь прав суперпользователя"

        # Входим как новый пользователь
        login_data = {"username": user_data["email"], "password": user_data["password"]}

        login_response = await async_client.post(
            "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert login_response.status_code == 200, f"Ошибка входа: {login_response.text}"
        token = login_response.json()["access_token"]

        # Получаем информацию о пользователе
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        me_response = await async_client.get("/users/me", headers=headers)
        assert me_response.status_code == 200, f"Ошибка получения данных пользователя: {me_response.text}"

        user_info = me_response.json()
        assert user_info["email"] == user_data["email"]
        assert not user_info.get("is_moderator", False)
        assert not user_info.get("is_superuser", False)

        test_stats["integration"]["passed"] += 1
    except Exception as e:
        print(f"Тест не пройден: {str(e)}")
        raise


@pytest.mark.asyncio
async def test_error_handling(async_client: AsyncClient, test_admin: User):
    """Тест обработки ошибок"""
    test_stats["integration"]["total"] += 1
    try:
        # Попытка регистрации с существующим email
        existing_user_data = {
            "email": test_admin.email,  # Используем email существующего администратора
            "password": test_admin.plain_password,
            "is_active": True,
        }

        register_response = await async_client.post("/auth/register", json=existing_user_data)
        assert (
            register_response.status_code == 409
        ), f"Ожидался код 409 (Conflict), получен {register_response.status_code}: {register_response.text}"
        error_data = register_response.json()
        assert "detail" in error_data, "В ответе должно быть поле detail"
        assert (
            "уже существует" in error_data["detail"].lower()
        ), "Сообщение об ошибке должно указывать на существующий email"

        # Попытка входа с неверными данными
        invalid_login_data = {"username": test_admin.email, "password": "wrong_password"}

        login_response = await async_client.post(
            "/auth/jwt/login", data=invalid_login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert (
            login_response.status_code == 400
        ), f"Ожидался код 400 (Bad Request), получен {login_response.status_code}: {login_response.text}"
        error_data = login_response.json()
        assert "detail" in error_data, "В ответе должно быть поле detail"

        # Попытка доступа к защищенному ресурсу без токена
        me_response = await async_client.get("/users/me")
        assert (
            me_response.status_code == 401
        ), f"Ожидался код 401 (Unauthorized), получен {me_response.status_code}: {me_response.text}"
        error_data = me_response.json()
        assert "detail" in error_data, "В ответе должно быть поле detail"

        test_stats["integration"]["passed"] += 1
    except Exception as e:
        print(f"Тест не пройден: {str(e)}")
        raise


@pytest.mark.asyncio
async def test_full_book_workflow(async_client: AsyncClient, auth_headers: dict):
    """Тест полного цикла работы с книгой"""
    test_stats["integration"]["total"] += 1
    try:
        # Создаем новую книгу
        book_data = {
            "title": "Test Book API",
            "year": "2024",  # Изменено на строку
            "publisher": "Test Publisher",
            "isbn": "978-3-16-148410-0",
            "description": "Test book description",
            "cover": None,
            "language": "ru",  # Явно указываем "ru"
            "file_url": "test_url",
            "authors": [],  # Пустые списки для связей
            "categories": [],
            "tags": [],
        }

        response = await async_client.post("/books/", json=book_data, headers=auth_headers)
        assert response.status_code == 201, f"Ошибка создания книги: {response.text}"
        created_book = response.json()

        # Проверяем, что книга создана с правильными данными
        assert created_book["title"] == book_data["title"]
        assert created_book["year"] == book_data["year"]
        assert created_book["isbn"] == book_data["isbn"]
        assert created_book["language"] == book_data["language"]
        assert created_book["authors"] == []
        assert created_book["categories"] == []
        assert created_book["tags"] == []

        # Получаем книгу
        response = await async_client.get(f"/books/{created_book['id']}", headers=auth_headers)
        assert response.status_code == 200, f"Ошибка получения книги: {response.text}"
        retrieved_book = response.json()
        assert retrieved_book["id"] == created_book["id"]

        # Обновляем книгу
        update_data = {"title": "Updated Test Book", "description": "Updated description", "language": Language.EN}
        response = await async_client.patch(f"/books/{created_book['id']}", headers=auth_headers, json=update_data)
        assert response.status_code == 200, f"Ошибка обновления книги: {response.text}"
        updated_book = response.json()
        assert updated_book["title"] == update_data["title"]
        assert updated_book["language"] == Language.EN

        # Удаляем книгу
        response = await async_client.delete(f"/books/{created_book['id']}", headers=auth_headers)
        assert response.status_code == 204, f"Ошибка удаления книги: {response.text}"

        # Проверяем, что книга удалена
        response = await async_client.get(f"/books/{created_book['id']}", headers=auth_headers)
        assert response.status_code == 404, "Книга должна быть удалена"

        test_stats["integration"]["passed"] += 1
    except Exception as e:
        print(f"Тест не пройден: {str(e)}")
        raise

    finally:
        # Очищаем тестовые данные
        try:
            # Сначала удаляем книгу, если она существует
            if "created_book" in locals():
                await async_client.delete(f"/books/{created_book['id']}", headers=auth_headers)
        except Exception as e:
            print(f"Ошибка при очистке тестовых данных: {e}")
