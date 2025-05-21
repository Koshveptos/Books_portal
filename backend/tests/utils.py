"""
Утилиты для тестирования
"""

from datetime import datetime, timedelta

from jose import jwt

from app.core.config import settings


def create_test_token(data: dict) -> str:
    """
    Создает тестовый JWT токен.

    Args:
        data: Данные для включения в токен

    Returns:
        str: JWT токен
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
