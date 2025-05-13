"""
Скрипт для создания тестового пользователя
"""

import asyncio

import httpx


async def create_test_user():
    """
    Создает тестового пользователя
    """
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Регистрация нового пользователя
        user_data = {"email": "test@example.com", "password": "Test1234!", "is_active": True}

        print(f"Регистрация пользователя: {user_data['email']}")

        response = await client.post("/auth/register", json=user_data)

        print(f"Код ответа: {response.status_code}")
        print(f"Тело ответа: {response.text}")

        if response.status_code == 201:
            print("Пользователь успешно создан")

            # Пробуем войти с новыми учетными данными
            login_data = {"username": user_data["email"], "password": user_data["password"]}

            print("\nПроверка авторизации")
            login_response = await client.post(
                "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            print(f"Код ответа: {login_response.status_code}")
            print(f"Тело ответа: {login_response.text}")
        else:
            print("Ошибка создания пользователя")


if __name__ == "__main__":
    asyncio.run(create_test_user())
