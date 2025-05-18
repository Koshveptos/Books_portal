"""
Настройки приложения.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Настройки приложения.
    """

    # Основные настройки
    PROJECT_NAME: str = "Books Portal"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Настройки безопасности
    # Используем фиксированный секретный ключ для отладки
    SECRET_KEY: str = "TEST_SECRET_KEY_FOR_DEBUGGING_JWT_ISSUES_NOT_FOR_PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней

    # Настройки базы данных
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "books_portal"
    DB_ECHO: bool = False

    @property
    def DATABASE_URL(self) -> str:
        """
        Получение URL для подключения к базе данных.
        """
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Настройки CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Настройки логирования
    LOG_LEVEL: str = "INFO"

    # Настройки Redis
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # Настройки приложения
    APP_NAME: str = "Books Portal"
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="allow"
    )


# Создание экземпляра настроек
settings = Settings()
