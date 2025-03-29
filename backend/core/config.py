from os import getenv

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str = "postgresql+asyncpg://postgres:1809kazak@localhost:5432/books"



settings = Settings()
