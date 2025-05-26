"""
Простой тест авторизации через JWT
"""

import json

import httpx
import pytest


@pytest.mark.asyncio
async def test_login(async_client: httpx.AsyncClient, test_admin):
    """
    Тест авторизации через JWT с использованием тестового администратора
    """
    email = test_admin.email
    password = test_admin.plain_password

    # Авторизация
    login_data = {"username": email, "password": password}

    print(f"Попытка авторизации для: {email}")

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = await async_client.post("/auth/jwt/login", data=login_data, headers=headers)

    print(f"Код ответа: {response.status_code}")
    print(f"Тело ответа: {response.text}")

    assert response.status_code == 200, "Ошибка авторизации"
    data = response.json()
    token = data.get("access_token")
    token_type = data.get("token_type", "bearer")

    print(f"Токен получен: {token[:20]}..." if token else "Токен не получен")
    print(f"Тип токена: {token_type}")

    # Проверка пользователя с полученным токеном
    auth_header = {"Authorization": f"Bearer {token}"}
    print(f"Заголовок авторизации: {auth_header}")

    # Проверка эндпоинта Me
    print("\nПроверка /users/me...")
    me_response = await async_client.get("/users/{user_id}/status", headers=auth_header)

    print(f"Код ответа: {me_response.status_code}")
    print(f"Данные пользователя: {me_response.text}")
    assert me_response.status_code == 200, "Ошибка получения данных пользователя"

    # Проверка эндпоинта status
    print("\nПроверка /auth/status...")
    status_response = await async_client.get("/auth/status", headers=auth_header)

    print(f"Код ответа: {status_response.status_code}")
    print(f"Данные статуса: {status_response.text}")
    assert status_response.status_code == 200, "Ошибка проверки статуса"
    assert "authenticated" in status_response.text, "Пользователь не аутентифицирован"

    # Проверка создания книги
    book_data = {
        "title": "Тестовая книга",
        "description": "Тест JWT авторизации",
        "author_name": "Тестовый Автор",
        "year": 2025,
        "language": "ru",
        "isbn": "978-3-16-148410-0",
        "categories": [],
        "tags": [],
    }

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    print("\nСоздание тестовой книги...")
    print(f"Заголовки: {headers}")
    print(f"Данные книги: {json.dumps(book_data, ensure_ascii=False)}")

    book_response = await async_client.post("/books/books/", json=book_data, headers=headers)

    print(f"Код ответа: {book_response.status_code}")
    print(f"Тело ответа: {book_response.text}")
    assert book_response.status_code == 201, "Ошибка создания книги"
