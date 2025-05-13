"""
Тестовый HTTP клиент с поддержкой JWT авторизации
"""

import asyncio
import json
import uuid

import httpx

BASE_URL = "http://localhost:8000"


class JWTClient:
    """
    HTTP клиент с поддержкой JWT авторизации
    """

    def __init__(self, base_url=BASE_URL):
        """
        Инициализация клиента
        """
        self.base_url = base_url
        self.token = None
        self.headers = {"Content-Type": "application/json"}
        self.client = httpx.AsyncClient(base_url=base_url, follow_redirects=True)

    async def login(self, username, password):
        """
        Авторизация и получение JWT токена
        """
        login_data = {"username": username, "password": password}

        response = await self.client.post(
            "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code != 200:
            print(f"Ошибка авторизации: {response.status_code}")
            print(response.text)
            return False

        data = response.json()
        self.token = data.get("access_token")

        if self.token:
            # Добавляем токен в заголовки для всех последующих запросов
            self.headers["Authorization"] = f"Bearer {self.token}"
            return True

        return False

    async def get_current_user(self):
        """
        Получение информации о текущем пользователе
        """
        response = await self.client.get("/users/me", headers=self.headers)
        if response.status_code != 200:
            print(f"Ошибка получения пользователя: {response.status_code}")
            print(response.text)
            return None

        return response.json()

    async def create_book(self, book_data):
        """
        Создание новой книги
        """
        response = await self.client.post("/books/books/", json=book_data, headers=self.headers)

        if response.status_code not in (200, 201):
            print(f"Ошибка создания книги: {response.status_code}")
            print(response.text)
            return None

        return response.json()

    async def close(self):
        """
        Закрытие клиента
        """
        await self.client.aclose()


async def test_jwt_workflow():
    """
    Тестирование полного цикла работы с JWT
    """
    client = JWTClient()

    try:
        # 1. Авторизация
        print("Попытка авторизации...")
        email = "123456@example.com"
        password = "123456"

        print(f"Email: {email}")
        print(f"Password: {password}")

        auth_result = await client.login(email, password)
        if not auth_result:
            print("Ошибка авторизации")
            return

        print("Успешная авторизация!")
        print(f"Токен: {client.token[:20]}..." if client.token else "Токен не получен")

        # 2. Получение информации о пользователе
        print("\nПолучение информации о пользователе...")
        print(f"Заголовки: {client.headers}")

        user = await client.get_current_user()
        if not user:
            print("Ошибка получения информации о пользователе")
            return

        print(f"Текущий пользователь: {user['email']}")
        print(f"ID пользователя: {user['id']}")
        print(f"Модератор: {user.get('is_moderator', False)}")

        # 3. Создание книги
        print("\nСоздание книги...")
        book_data = {
            "title": f"Тестовая книга {uuid.uuid4().hex[:8]}",
            "description": "Книга для тестирования JWT авторизации",
            "author_name": "Тестовый Автор",
            "year": 2025,
            "isbn": f"978-3-16-148410-{uuid.uuid4().hex[:1]}",
            "language": "ru",
            "categories": [],
            "tags": [],
        }

        print(f"Данные книги: {json.dumps(book_data, ensure_ascii=False)}")

        book = await client.create_book(book_data)
        if not book:
            print("Ошибка создания книги")
            return

        print(f"Книга успешно создана: {book['title']}")
        print(f"ID книги: {book['id']}")

        print("\nТест успешно пройден!")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_jwt_workflow())
