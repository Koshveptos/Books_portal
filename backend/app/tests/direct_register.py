"""
Скрипт для прямого создания тестового пользователя в базе данных
"""

import asyncio
import sys

from core.auth import get_user_db
from core.database import get_db
from fastapi_users.password import PasswordHelper


async def create_test_user(email: str, password: str):
    """
    Создать тестового пользователя напрямую через базу данных
    """
    print(f"Создание пользователя: {email}")

    # Получаем зависимости
    password_helper = PasswordHelper()
    async for user_db in get_user_db(await anext(get_db())):
        # Проверяем, существует ли уже пользователь с таким email
        existing_user = await user_db.get_by_email(email)
        if existing_user:
            print(f"Пользователь с email {email} уже существует!")
            print(f"ID: {existing_user.id}")
            print(f"Модератор: {existing_user.is_moderator}")
            print(f"Активен: {existing_user.is_active}")
            return

        # Хешируем пароль
        hashed_password = password_helper.hash(password)
        print(f"Пароль захеширован: {hashed_password[:20]}...")

        # Создаем пользователя
        user_dict = {
            "email": email,
            "hashed_password": hashed_password,
            "is_active": True,
            "is_superuser": True,
            "is_verified": True,
            "is_moderator": True,
        }
        user = await user_db.create(user_dict)

        print("Пользователь создан!")
        print(f"ID: {user.id}")
        print(f"Email: {user.email}")
        print(f"Модератор: {user.is_moderator}")


if __name__ == "__main__":
    # Получаем email и пароль из аргументов командной строки или используем значения по умолчанию
    email = sys.argv[1] if len(sys.argv) > 1 else "test@example.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "Test123$"

    asyncio.run(create_test_user(email, password))
