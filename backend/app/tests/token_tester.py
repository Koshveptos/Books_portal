"""
Скрипт для тестирования конкретного JWT токена
"""

import base64
import json
import sys

import requests


def decode_jwt(token):
    """
    Декодирует JWT токен (только для отладки)
    """
    parts = token.split(".")
    if len(parts) != 3:
        print("Неверный формат JWT токена")
        return None

    try:
        # Декодируем вторую часть (payload)
        payload = parts[1]
        # Добавляем = если необходимо для правильного base64 декодирования
        payload += "=" * (4 - len(payload) % 4) if len(payload) % 4 else ""
        decoded = base64.b64decode(payload).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        print(f"Ошибка декодирования JWT: {str(e)}")
        return None


def test_token(token):
    """
    Тестирует JWT токен для аутентификации
    """
    print(f"Тестирование токена: {token[:30]}...")

    # Декодируем токен для отладки
    decoded = decode_jwt(token)
    if decoded:
        print(f"Содержимое токена: {json.dumps(decoded, ensure_ascii=False)}")
        print(f"ID пользователя в токене: {decoded.get('sub')}")
        print(f"Срок действия токена: {decoded.get('exp')}")

    # Создаем заголовок для авторизации
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Заголовок Authorization: {headers['Authorization']}")

    # Проверяем структуру заголовка
    auth_parts = headers["Authorization"].split(" ")
    if len(auth_parts) != 2 or auth_parts[0] != "Bearer":
        print("ОШИБКА: Неправильный формат заголовка Authorization!")
    else:
        print("Формат заголовка Authorization корректен")

    # Базовый URL API
    base_url = "http://localhost:8000"

    try:
        # Ручная отправка запроса на статус, детальная диагностика
        print("\nОтладка запроса auth/status")
        session = requests.Session()
        req = requests.Request("GET", f"{base_url}/auth/status", headers=headers)
        prepared = session.prepare_request(req)

        print(f"URL запроса: {prepared.url}")
        print(f"Метод запроса: {prepared.method}")
        print("Заголовки запроса:")
        for key, value in prepared.headers.items():
            print(f"  {key}: {value}")

        response = session.send(prepared)
        print(f"Статус ответа: {response.status_code}")
        print("Заголовки ответа:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print(f"Текст ответа: {response.text}")

        # Проверяем /users/me с подробной диагностикой
        print("\nОтладка запроса /users/me")
        req = requests.Request("GET", f"{base_url}/users/me", headers=headers)
        prepared = session.prepare_request(req)

        print(f"URL запроса: {prepared.url}")
        print(f"Метод запроса: {prepared.method}")
        print("Заголовки запроса:")
        for key, value in prepared.headers.items():
            print(f"  {key}: {value}")

        response = session.send(prepared)
        print(f"Статус ответа: {response.status_code}")
        print("Заголовки ответа:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print(f"Текст ответа: {response.text}")

    except Exception as e:
        print(f"Ошибка при выполнении запросов: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        token = sys.argv[1]
        test_token(token)
    else:
        print("Необходимо указать JWT токен")
        print("Пример: python -m tests.token_tester <ваш_токен>")
