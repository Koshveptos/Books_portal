"""
Тесты для проверки авторизации при работе с книгами через JWT токены.
"""

import asyncio
import random

import httpx

# URL API для тестирования
BASE_URL = "http://localhost:8000"


async def test_create_book_with_jwt():
    """
    Проверяет авторизацию и создание книги:
    1. Получение JWT токена
    2. Создание книги с JWT токеном модератора
    """
    async with httpx.AsyncClient() as client:
        # 1. Вход в систему
        login_data = {"username": "123456@example.com", "password": "123456"}  # используйте существующий аккаунт

        login_response = await client.post(
            f"{BASE_URL}/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        print(f"Вход: {login_response.status_code}")

        if login_response.status_code != 200:
            print(f"Ошибка при входе: {login_response.text}")
            return False

        # Получение токена
        token_data = login_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            print("Токен не получен")
            return False

        print(f"Токен получен: {access_token[:20]}...")

        # 2. Проверка /me для подтверждения авторизации
        me_response = await client.get(f"{BASE_URL}/users/me", headers={"Authorization": f"Bearer {access_token}"})

        print(f"Проверка /me: {me_response.status_code}")

        if me_response.status_code != 200:
            print(f"Ошибка при проверке /me: {me_response.text}")
            return False

        # 3. Создание новой книги с JWT токеном
        book_data = {
            "title": f"Test Book {random.randint(1, 1000)}",
            "description": "Тестовая книга для проверки JWT авторизации",
            "author_name": "Test Author",
            "year": 2023,
            "isbn": f"978-3-16-148410-{random.randint(0, 9)}",
            "language": "ru",
            "categories": [],
            "tags": [],
        }

        book_response = await client.post(
            f"{BASE_URL}/books/books/", json=book_data, headers={"Authorization": f"Bearer {access_token}"}
        )

        print(f"Создание книги: {book_response.status_code}")
        print(book_response.text)

        if book_response.status_code != 200 and book_response.status_code != 201:
            print(f"Ошибка при создании книги: {book_response.text}")
            return False

        print("Тест создания книги с JWT токеном успешно пройден!")
        return True


if __name__ == "__main__":
    # Запуск теста
    asyncio.run(test_create_book_with_jwt())
