"""
Модульные тесты для аутентификации
"""

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_user(async_client: AsyncClient):
    """Тест регистрации нового пользователя"""
    user_data = {
        "email": f"test_register_{uuid.uuid4().hex[:8]}@example.com",
        "password": "Test1234!",
        "is_active": True,
    }

    response = await async_client.post("/auth/register", json=user_data)
    assert response.status_code == 201, f"Ошибка регистрации: {response.text}"
    data = response.json()
    assert "id" in data
    assert data["email"] == user_data["email"]
    assert "password" not in data  # Пароль не должен возвращаться


async def test_login_user(async_client: AsyncClient):
    """Тест входа пользователя"""
    # Сначала регистрируем пользователя
    user_data = {"email": f"test_login_{uuid.uuid4().hex[:8]}@example.com", "password": "Test1234!", "is_active": True}

    register_response = await async_client.post("/auth/register", json=user_data)
    assert register_response.status_code == 201, f"Ошибка регистрации: {register_response.text}"

    # Пробуем войти
    login_data = {"username": user_data["email"], "password": user_data["password"]}

    response = await async_client.post(
        "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    assert response.status_code == 200, f"Ошибка входа: {response.text}"
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_invalid_login(async_client: AsyncClient):
    """Тест входа с неверными данными"""
    login_data = {"username": "nonexistent@example.com", "password": "wrongpassword"}

    response = await async_client.post(
        "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    assert response.status_code == 400, f"Ожидался код 400, получен {response.status_code}: {response.text}"


async def test_get_current_user(async_client: AsyncClient, auth_headers: dict):
    """Тест получения информации о текущем пользователе"""
    response = await async_client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200, f"Ошибка получения данных пользователя: {response.text}"
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert "password" not in data


async def test_invalid_token(async_client: AsyncClient):
    """Тест доступа с неверным токеном"""
    headers = {"Authorization": "Bearer invalid_token", "Content-Type": "application/json"}

    response = await async_client.get("/users/me", headers=headers)
    assert response.status_code == 401, f"Ожидался код 401, получен {response.status_code}: {response.text}"
