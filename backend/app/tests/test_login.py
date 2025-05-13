"""
Простой тест авторизации через JWT
"""

import asyncio
import getpass
import json
import sys

import httpx


async def test_login(email=None, password=None):
    """
    Тест авторизации через JWT с возможностью ввода пароля
    """
    if not email:
        email = input("Введите email: ")

    if not password:
        password = getpass.getpass("Введите пароль: ")

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Авторизация
        login_data = {"username": email, "password": password}

        print(f"Попытка авторизации для: {email}")

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = await client.post("/auth/jwt/login", data=login_data, headers=headers)

        print(f"Код ответа: {response.status_code}")
        print(f"Тело ответа: {response.text}")

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            token_type = data.get("token_type", "bearer")

            print(f"Токен получен: {token[:20]}..." if token else "Токен не получен")
            print(f"Тип токена: {token_type}")

            # Проверка пользователя с полученным токеном
            # ВАЖНО: формат должен быть строго "Bearer токен" с пробелом между типом и токеном
            auth_header = {"Authorization": f"Bearer {token}"}
            print(f"Заголовок авторизации: {auth_header}")

            # Проверка эндпоинта Me
            print("\nПроверка /users/me...")
            me_response = await client.get("/users/me", headers=auth_header)

            print(f"Код ответа: {me_response.status_code}")
            print(f"Данные пользователя: {me_response.text}")

            # Проверка эндпоинта status
            print("\nПроверка /auth/status...")
            status_response = await client.get("/auth/status", headers=auth_header)

            print(f"Код ответа: {status_response.status_code}")
            print(f"Данные статуса: {status_response.text}")

            # Если проверка статуса успешна, попробуем создать книгу
            if status_response.status_code == 200 and "authenticated" in status_response.text:
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

                book_response = await client.post("/books/books/", json=book_data, headers=headers)

                print(f"Код ответа: {book_response.status_code}")
                print(f"Тело ответа: {book_response.text}")
        else:
            print("Авторизация не удалась")


if __name__ == "__main__":
    # Если передали пользователя и пароль в аргументах - используем их
    email = sys.argv[1] if len(sys.argv) > 1 else None
    password = sys.argv[2] if len(sys.argv) > 2 else None

    asyncio.run(test_login(email, password))
