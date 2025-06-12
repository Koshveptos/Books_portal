import json
from datetime import datetime
from typing import Any, Dict

from app.schemas.book import AuthorResponse, BookRecommendation, BookResponse, RecommendationStats


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (BookResponse, AuthorResponse, BookRecommendation, RecommendationStats)):
            return obj.model_dump()
        return super().default(obj)


def serialize_to_json(obj: Any) -> str:
    """
    Сериализует объект в JSON строку с поддержкой специальных типов.

    Args:
        obj: Объект для сериализации

    Returns:
        str: JSON строка
    """
    return json.dumps(obj, cls=CustomJSONEncoder)


def deserialize_from_json(json_str: str) -> Dict:
    """
    Десериализует JSON строку в словарь.

    Args:
        json_str: JSON строка

    Returns:
        Dict: Десериализованный словарь
    """
    return json.loads(json_str)
