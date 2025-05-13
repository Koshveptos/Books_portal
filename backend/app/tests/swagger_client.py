"""
Тестовый клиент для подключения к Swagger UI
"""

import json
import sys

import requests

# URL API для тестирования
BASE_URL = "http://localhost:8000"


def test_login_with_requests(email="123456@example.com", password="123456"):
    """
    Тест авторизации через requests - более простая библиотека
    """
    print(f"Тестирование авторизации с requests: {email}")

    # 1. Авторизация
    login_url = f"{BASE_URL}/auth/jwt/login"
    login_data = {"username": email, "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    print(f"Отправка запроса: POST {login_url}")
    print(f"Данные: {login_data}")
    print(f"Заголовки: {headers}")

    try:
        response = requests.post(login_url, data=login_data, headers=headers)
        print(f"Статус ответа: {response.status_code}")
        print(f"Текст ответа: {response.text}")

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            token_type = token_data.get("token_type", "bearer")

            print(f"Токен получен: {access_token[:30]}..." if access_token else "Токен не получен")
            print(f"Тип токена: {token_type}")

            # 2. Проверка /users/me
            me_url = f"{BASE_URL}/users/me"
            auth_header = {"Authorization": f"Bearer {access_token}"}

            print("\nПроверка /users/me")
            print(f"URL: {me_url}")
            print(f"Заголовки: {auth_header}")

            me_response = requests.get(me_url, headers=auth_header)
            print(f"Статус ответа: {me_response.status_code}")
            print(f"Текст ответа: {me_response.text}")

            # 3. Проверка статуса авторизации
            status_url = f"{BASE_URL}/auth/status"

            print("\nПроверка /auth/status")
            print(f"URL: {status_url}")

            status_response = requests.get(status_url, headers=auth_header)
            print(f"Статус ответа: {status_response.status_code}")
            print(f"Текст ответа: {status_response.text}")

            # 4. Проверка создания книги
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get("authenticated"):
                    print("\nПользователь авторизован, пробуем создать книгу")

                    book_url = f"{BASE_URL}/books/books/"
                    book_data = {
                        "title": "Тестовая книга requests",
                        "description": "Книга для тестирования JWT авторизации",
                        "author_name": "Test Author",
                        "year": 2023,
                        "language": "ru",
                        "isbn": "978-3-16-148410-0",
                        "categories": [],
                        "tags": [],
                    }

                    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}

                    print(f"URL: {book_url}")
                    print(f"Заголовки: {headers}")
                    print(f"Данные: {json.dumps(book_data, ensure_ascii=False)}")

                    book_response = requests.post(book_url, json=book_data, headers=headers)
                    print(f"Статус ответа: {book_response.status_code}")
                    print(f"Текст ответа: {book_response.text}")
    except Exception as e:
        print(f"Ошибка: {str(e)}")


if __name__ == "__main__":
    # Если параметры переданы через командную строку - используем их
    email = sys.argv[1] if len(sys.argv) > 1 else "123456@example.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "123456"

    test_login_with_requests(email, password)
