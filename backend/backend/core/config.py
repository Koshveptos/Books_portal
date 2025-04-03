from os import getenv

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:12345678@localhost:5432/books_portal"



settings = Settings()
