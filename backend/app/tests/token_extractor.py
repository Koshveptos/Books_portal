"""
Скрипт для просмотра и анализа JWT токена
"""

import base64
import json
import sys

import jwt
import requests

# Если вы знаете токен, просто вставьте его здесь
TOKEN = ""


def parse_jwt(token):
    """
    Разобрать JWT токен без проверки подписи
    """
    if not token:
        print("Токен не предоставлен!")
        return

    try:
        # Декодируем без проверки подписи
        data = jwt.decode(token, options={"verify_signature": False})

        print("Данные JWT токена:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Проверяем структуру (fastapi-users обычно использует эти поля)
        if "sub" in data:
            print(f"ID пользователя (sub): {data['sub']}")
        if "aud" in data:
            print(f"Аудитория (aud): {data['aud']}")
        if "exp" in data:
            print(f"Время истечения (exp): {data['exp']}")

        # Разбираем заголовок
        parts = token.split(".")
        if len(parts) >= 1:
            # Добавляем дополнительное выравнивание, если нужно
            header_part = parts[0]
            header_part = header_part + "=" * (4 - len(header_part) % 4)

            try:
                header_json = base64.b64decode(header_part).decode("utf-8")
                header = json.loads(header_json)
                print("\nЗаголовок JWT:")
                print(json.dumps(header, indent=2, ensure_ascii=False))

                # Проверяем алгоритм
                if "alg" in header:
                    print(f"Алгоритм подписи: {header['alg']}")
            except Exception as e:
                print(f"Ошибка при разборе заголовка: {str(e)}")

    except Exception as e:
        print(f"Ошибка при декодировании токена: {str(e)}")


def get_token_from_api(username, password):
    """
    Получить токен через API
    """
    try:
        login_data = {"username": username, "password": password}

        response = requests.post(
            "http://localhost:8000/auth/jwt/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print(f"Получен токен: {token}")
                return token
            else:
                print("Токен не получен в ответе API")
                return None
        else:
            print(f"Ошибка при запросе токена: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Ошибка при запросе токена: {str(e)}")
        return None


if __name__ == "__main__":
    # Если токен передан как аргумент - используем его
    token = sys.argv[1] if len(sys.argv) > 1 else TOKEN

    # Если нет токена, но есть учетные данные - пробуем получить токен через API
    if not token and len(sys.argv) > 2:
        username = sys.argv[1]
        password = sys.argv[2]
        print(f"Попытка получения токена для {username}")
        token = get_token_from_api(username, password)

    if token:
        parse_jwt(token)
    else:
        print("Необходимо предоставить JWT токен или учетные данные для входа")
        print("Использование: python -m tests.token_extractor <токен>")
        print("или: python -m tests.token_extractor <username> <password>")
