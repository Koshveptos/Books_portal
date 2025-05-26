"""
Скрипт для анализа структуры базы данных PostgreSQL
"""

from loguru import logger
from pydantic_settings import BaseSettings
from sqlalchemy import MetaData, create_engine, inspect


class DatabaseSettings(BaseSettings):
    """Настройки подключения к базе данных"""

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/books_portal"


def inspect_database():
    """Анализ структуры базы данных"""
    settings = DatabaseSettings()

    try:
        # Создаем подключение к базе данных
        engine = create_engine(settings.DATABASE_URL)
        metadata = MetaData()
        metadata.reflect(bind=engine)

        inspector = inspect(engine)

        # Получаем список схем
        schemas = inspector.get_schema_names()

        for schema in schemas:
            logger.info(f"\n=== Схема: {schema} ===")

            # Получаем список таблиц в схеме
            for table_name in inspector.get_table_names(schema=schema):
                logger.info(f"\nТаблица: {table_name}")

                # Получаем информацию о колонках
                columns = inspector.get_columns(table_name, schema=schema)
                logger.info("  Колонки:")
                for column in columns:
                    col_name = column["name"]
                    col_type = column["type"]
                    nullable = "nullable" if column["nullable"] else "NOT NULL"
                    default = f", default={column['default']}" if column.get("default") else ""
                    logger.info(f"   - {col_name}: {col_type} ({nullable}{default})")

                # Получаем информацию о первичных ключах
                primary_keys = inspector.get_pk_constraint(table_name, schema=schema)
                if primary_keys["constrained_columns"]:
                    logger.info(f"  Первичный ключ: {primary_keys['constrained_columns']}")

                # Получаем информацию о внешних ключах
                foreign_keys = inspector.get_foreign_keys(table_name, schema=schema)
                if foreign_keys:
                    logger.info("  Внешние ключи:")
                    for fk in foreign_keys:
                        name = fk["name"]
                        from_col = fk["constrained_columns"]
                        to_table = fk["referred_table"]
                        to_col = fk["referred_columns"]
                        logger.info(f"   - {name}: {from_col} → {to_table}({to_col})")

                # Получаем информацию об индексах
                indexes = inspector.get_indexes(table_name, schema=schema)
                if indexes:
                    logger.info("  Индексы:")
                    for index in indexes:
                        name = index["name"]
                        columns = index["column_names"]
                        unique = "UNIQUE" if index["unique"] else ""
                        logger.info(f"   - {name} {unique}: {columns}")

                logger.info("-" * 50)

    except Exception as e:
        logger.error(f"Ошибка при анализе базы данных: {e}")
        raise


if __name__ == "__main__":
    inspect_database()
