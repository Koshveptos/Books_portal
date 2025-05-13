"""
Тесты для проверки аутентификации через JWT токены.
"""

import asyncio
import os

import httpx

# URL API для тестирования
BASE_URL = "http://localhost:8000"


async def test_jwt_authentication():
    """
    Проверяет аутентификацию через JWT токены:
    1. Регистрация нового пользователя
    2. Вход с учетными данными и получение JWT токена
    3. Проверка доступа к защищенному эндпоинту с токеном
    """
    async with httpx.AsyncClient() as client:
        # 1. Регистрация пользователя
        email = f"test_user_{os.urandom(4).hex()}@example.com"
        password = "Test1234!"

        register_data = {"email": email, "password": password, "is_active": True}

        register_response = await client.post(f"{BASE_URL}/auth/register", json=register_data)

        print(f"Регистрация: {register_response.status_code}")
        print(register_response.text)

        if register_response.status_code != 201:
            print("Ошибка при регистрации пользователя")
            return False

        # 2. Вход в систему
        login_data = {"username": email, "password": password}

        login_response = await client.post(
            f"{BASE_URL}/auth/jwt/login",
            data=login_data,  # form-data, не JSON!
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        print(f"Вход: {login_response.status_code}")
        print(login_response.text)

        if login_response.status_code != 200:
            print("Ошибка при входе в систему")
            return False

        # Получение токена
        token_data = login_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            print("Токен не получен")
            return False

        print(f"Токен получен: {access_token[:20]}...")

        # 3. Проверка защищенного эндпоинта
        me_response = await client.get(f"{BASE_URL}/users/me", headers={"Authorization": f"Bearer {access_token}"})

        print(f"Проверка /me: {me_response.status_code}")
        print(me_response.text)

        if me_response.status_code != 200:
            print("Ошибка при доступе к защищенному эндпоинту")
            return False

        # Проверяем, что данные пользователя верны
        user_data = me_response.json()
        if user_data.get("email") != email:
            print("Неверные данные пользователя")
            return False

        print("Тест JWT аутентификации успешно пройден!")
        return True


if __name__ == "__main__":
    # Запуск теста
    asyncio.run(test_jwt_authentication())
