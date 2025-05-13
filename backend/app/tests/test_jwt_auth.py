"""
Полный тест JWT авторизации
"""

import asyncio
import json
import sys
from typing import Dict, Optional

import httpx

# URL API для тестирования
BASE_URL = "http://localhost:8000"


class JWTAuthTest:
    """
    Класс для тестирования JWT авторизации
    """

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, follow_redirects=True)
        self.token = None
        self.user_data = None

    async def login(self, username: str, password: str) -> bool:
        """
        Авторизация через JWT
        """
        print(f"Авторизация пользователя: {username}")

        # Формируем данные для входа (минимально необходимые)
        login_data = {
            "username": username,
            "password": password,
        }

        # Отправляем запрос на авторизацию
        try:
            response = await self.client.post(
                "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            print(f"Статус авторизации: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                token_type = data.get("token_type", "bearer")

                print(f"Токен получен: {self.token[:30]}..." if self.token else "Токен не получен")
                print(f"Тип токена: {token_type}")
                return True
            else:
                print(f"Ошибка авторизации: {response.text}")
                return False
        except Exception as e:
            print(f"Исключение при авторизации: {str(e)}")
            return False

    async def get_headers(self) -> Dict[str, str]:
        """
        Получить заголовки с JWT-токеном
        """
        if not self.token:
            return {"Content-Type": "application/json"}

        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}

    async def get_current_user(self) -> Optional[Dict]:
        """
        Получить данные текущего пользователя
        """
        if not self.token:
            print("Невозможно получить пользователя: токен не получен")
            return None

        headers = await self.get_headers()

        print("\nПроверка эндпоинта /users/me")
        print(f"Заголовки: {headers}")

        try:
            response = await self.client.get("/users/me", headers=headers)

            print(f"Статус получения пользователя: {response.status_code}")

            if response.status_code == 200:
                self.user_data = response.json()
                print(f"Пользователь: {self.user_data}")
                return self.user_data
            else:
                print(f"Ошибка получения пользователя: {response.text}")
                return None
        except Exception as e:
            print(f"Исключение при получении пользователя: {str(e)}")
            return None

    async def check_auth_status(self) -> bool:
        """
        Проверить статус авторизации
        """
        if not self.token:
            print("Невозможно проверить статус: токен не получен")
            return False

        headers = await self.get_headers()

        print("\nПроверка эндпоинта /auth/status")

        try:
            response = await self.client.get("/auth/status", headers=headers)

            print(f"Статус проверки: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Статус авторизации: {data}")
                return data.get("authenticated", False)
            else:
                print(f"Ошибка проверки статуса: {response.text}")
                return False
        except Exception as e:
            print(f"Исключение при проверке статуса: {str(e)}")
            return False

    async def create_book(self) -> Optional[Dict]:
        """
        Создать тестовую книгу
        """
        if not self.token:
            print("Невозможно создать книгу: токен не получен")
            return None

        headers = await self.get_headers()

        # Данные для создания книги
        book_data = {
            "title": "Тестовая книга JWT авторизации",
            "description": "Книга создана для тестирования JWT авторизации",
            "author_name": "Test Author",
            "year": 2023,
            "language": "ru",
            "isbn": "978-3-16-148410-0",
            "categories": [],
            "tags": [],
        }

        print("\nСоздание тестовой книги")
        print("Запрос: POST /books/books/")
        print(f"Данные: {json.dumps(book_data, ensure_ascii=False)}")
        print(f"Заголовки: {headers}")

        try:
            response = await self.client.post("/books/books/", json=book_data, headers=headers)

            print(f"Статус создания книги: {response.status_code}")

            if response.status_code in (200, 201):
                book = response.json()
                print(f"Книга создана: {book.get('title')}")
                return book
            else:
                print(f"Ошибка создания книги: {response.text}")
                return None
        except Exception as e:
            print(f"Исключение при создании книги: {str(e)}")
            return None

    async def close(self):
        """
        Закрыть клиент
        """
        await self.client.aclose()


async def run_test(username: str, password: str):
    """
    Запустить полное тестирование JWT авторизации
    """
    tester = JWTAuthTest()

    try:
        print("Начало тестирования JWT авторизации")
        print(f"API URL: {tester.base_url}")
        print("-" * 60)

        # Шаг 1: Авторизация и получение токена
        auth_result = await tester.login(username, password)
        if not auth_result:
            print("Тест завершен: ошибка авторизации")
            return

        print("-" * 60)

        # Шаг 2: Проверка статуса авторизации
        status_result = await tester.check_auth_status()
        if not status_result:
            print("Тест завершен: статус авторизации отрицательный")
            return

        print("-" * 60)

        # Шаг 3: Получение данных пользователя
        user_result = await tester.get_current_user()
        if not user_result:
            print("Тест завершен: не удалось получить данные пользователя")
            return

        print("-" * 60)

        # Шаг 4: Создание книги
        book_result = await tester.create_book()
        if not book_result:
            print("Тест завершен: не удалось создать книгу")
            return

        print("-" * 60)
        print("ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("Все этапы JWT авторизации работают корректно")

    finally:
        await tester.close()


if __name__ == "__main__":
    # Если учетные данные переданы как аргументы - используем их
    # Иначе используем значения по умолчанию
    username = sys.argv[1] if len(sys.argv) > 1 else "123456@example.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "123456"

    asyncio.run(run_test(username, password))
