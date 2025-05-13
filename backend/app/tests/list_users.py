"""
Скрипт для просмотра списка пользователей в базе данных
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import async_session_maker
from models.user import User
from sqlalchemy import select


async def list_users():
    """
    Получить список всех пользователей в базе данных
    """
    print("Получение списка пользователей...")

    async with async_session_maker() as session:
        # Запрос всех пользователей
        result = await session.execute(select(User))
        users = result.scalars().all()

        print(f"Найдено пользователей: {len(users)}")
        print("-" * 50)

        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Активен: {user.is_active}")
            print(f"Супер-пользователь: {user.is_superuser}")
            print(f"Модератор: {user.is_moderator}")
            print(f"Верифицирован: {user.is_verified}")
            print("-" * 50)


if __name__ == "__main__":
    asyncio.run(list_users())
