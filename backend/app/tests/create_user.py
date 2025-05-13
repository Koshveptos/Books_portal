"""
Скрипт для создания пользователя через API и получения токена
"""

import json
import sys

import requests


def create_user(email, password):
    """
    Создать пользователя через API
    """
    print(f"Создание пользователя: {email}")

    user_data = {"email": email, "password": password, "is_active": True, "is_superuser": False, "is_verified": True}

    print("Запрос на регистрацию пользователя")
    print(f"Данные: {json.dumps(user_data, ensure_ascii=False)}")

    try:
        response = requests.post(
            "http://localhost:8000/auth/register", json=user_data, headers={"Content-Type": "application/json"}
        )

        print(f"Статус ответа: {response.status_code}")
        print(f"Текст ответа: {response.text}")

        if response.status_code == 201:
            print("Пользователь успешно создан!")

            # Получение токена
            print("\nПолучение токена доступа...")
            login_data = {"username": email, "password": password}

            login_response = requests.post(
                "http://localhost:8000/auth/jwt/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            print(f"Статус ответа логина: {login_response.status_code}")

            if login_response.status_code == 200:
                token_data = login_response.json()
                access_token = token_data.get("access_token")
                print(f"Токен доступа: {access_token}")
                return True, access_token
            else:
                print(f"Ошибка при получении токена: {login_response.text}")
                return True, None
        else:
            print("Ошибка при создании пользователя")
            return False, None
    except Exception as e:
        print(f"Исключение при создании пользователя: {str(e)}")
        return False, None


if __name__ == "__main__":
    # Получаем параметры из аргументов командной строки
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
        success, token = create_user(email, password)

        if success and token:
            print("\nТеперь вы можете использовать этот токен для тестирования:")
            print(f"python -m tests.token_tester {token}")
    else:
        print("Необходимо указать email и пароль")
        print("Пример: python -m tests.create_user test@example.com password123")
