"""
Скрипт для отладки значений перечисления language в базе данных.
"""

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Загружаем переменные окружения
load_dotenv(".env")

# Получаем URL базы данных из переменных окружения или используем значение по умолчанию
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/books_portal")


async def check_enum_values():
    """Проверяет значения перечисления language в базе данных."""
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        # Запрос для получения всех значений перечисления language
        result = await conn.execute(text("SELECT unnest(enum_range(NULL::language)) AS enum_value"))

        print("Значения перечисления language в базе данных:")
        for row in result:
            print(f"  - {row.enum_value}")

        # Попробуем также получить информацию о типе из системных таблиц
        result2 = await conn.execute(
            text(
                """
                SELECT t.typname AS enum_name, e.enumlabel AS enum_value
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = 'language'
                ORDER BY e.enumsortorder
            """
            )
        )

        print("\nИнформация о перечислении language из системных таблиц:")
        for row in result2:
            print(f"  - {row.enum_name}: {row.enum_value}")

    await engine.dispose()


# Точка входа для скрипта
if __name__ == "__main__":
    asyncio.run(check_enum_values())
