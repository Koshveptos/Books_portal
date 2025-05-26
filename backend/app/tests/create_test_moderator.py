"""
Скрипт для создания тестового модератора
"""

import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.auth import get_user_manager
from app.core.config import settings
from app.core.database import Base
from app.schemas.user import UserCreate


async def create_moderator():
    """Создает тестового модератора"""
    # Создаем движок базы данных
    engine = create_async_engine(settings.TEST_DATABASE_URL, echo=True)

    # Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Создаем сессию
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Создаем менеджер пользователей
        user_manager = get_user_manager()

        # Данные модератора
        moderator_email = "test_moderator@example.com"
        moderator_password = "Test1234!"

        try:
            # Создаем пользователя через FastAPI Users
            user_create = UserCreate(email=moderator_email, password=moderator_password, is_active=True)

            # Создаем пользователя
            moderator = await user_manager.create(user_create)

            # Устанавливаем права модератора
            moderator.is_moderator = False
            moderator.is_verified = False

            # Сохраняем изменения
            session.add(moderator)
            await session.commit()
            await session.refresh(moderator)

            print("\nТестовый модератор успешно создан!")
            print(f"Email: {moderator_email}")
            print(f"Пароль: {moderator_password}")
            print("\nЭти данные будут использоваться в тестах.")

        except Exception as e:
            print(f"\nОшибка при создании модератора: {str(e)}")
            await session.rollback()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_moderator())
