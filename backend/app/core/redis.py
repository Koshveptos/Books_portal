"""
Модуль для работы с Redis.
"""

import json
from typing import Any, Dict, Optional

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import CacheException
from app.core.logger_config import logger

# Глобальная переменная для хранения пула соединений Redis
redis_pool: Optional[ConnectionPool] = None


async def init_redis() -> None:
    """
    Инициализация подключения к Redis.
    """
    global redis_pool

    try:
        # Создаем пул соединений
        redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
            health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
        )

        # Проверяем подключение
        async with Redis(connection_pool=redis_pool) as redis:
            await redis.ping()

        logger.info("Redis connection initialized successfully")

    except RedisError as e:
        logger.critical(
            "Failed to initialize Redis connection",
            extra={"error": str(e), "error_type": type(e).__name__, "redis_url": settings.REDIS_URL},
        )
        raise CacheException("Failed to initialize Redis connection") from e


async def get_redis_client() -> Redis:
    """
    Получение клиента Redis.
    """
    if not redis_pool:
        raise CacheException("Redis connection not initialized")

    try:
        return Redis(connection_pool=redis_pool)
    except RedisError as e:
        logger.error("Failed to get Redis client", extra={"error": str(e), "error_type": type(e).__name__})
        raise CacheException("Failed to get Redis client") from e


async def set_cache(key: str, value: Any, expire: Optional[int] = None, redis_client: Optional[Redis] = None) -> bool:
    """
    Сохранение значения в кэш.

    Args:
        key: Ключ для сохранения
        value: Значение для сохранения
        expire: Время жизни в секундах
        redis_client: Клиент Redis (опционально)

    Returns:
        bool: True если успешно, False в случае ошибки
    """
    try:
        if not redis_client:
            redis_client = await get_redis_client()

        # Сериализуем значение в JSON
        serialized_value = json.dumps(value)

        # Сохраняем в Redis
        if expire:
            await redis_client.setex(key, expire, serialized_value)
        else:
            await redis_client.set(key, serialized_value)

        logger.debug(f"Cache set: {key}", extra={"key": key, "expire": expire})
        return True

    except (RedisError, json.JSONDecodeError) as e:
        logger.error(
            f"Failed to set cache: {key}",
            extra={"error": str(e), "error_type": type(e).__name__, "key": key, "expire": expire},
        )
        return False


async def get_cache(key: str, redis_client: Optional[Redis] = None) -> Optional[Any]:
    """
    Получение значения из кэша.

    Args:
        key: Ключ для получения
        redis_client: Клиент Redis (опционально)

    Returns:
        Any: Значение из кэша или None если не найдено
    """
    try:
        if not redis_client:
            redis_client = await get_redis_client()

        # Получаем значение из Redis
        value = await redis_client.get(key)

        if value is None:
            logger.debug(f"Cache miss: {key}")
            return None

        # Десериализуем значение из JSON
        try:
            deserialized_value = json.loads(value)
            logger.debug(f"Cache hit: {key}")
            return deserialized_value
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to deserialize cache value: {key}",
                extra={"error": str(e), "error_type": type(e).__name__, "key": key},
            )
            return None

    except RedisError as e:
        logger.error(f"Failed to get cache: {key}", extra={"error": str(e), "error_type": type(e).__name__, "key": key})
        return None


async def delete_cache(key: str, redis_client: Optional[Redis] = None) -> bool:
    """
    Удаление значения из кэша.

    Args:
        key: Ключ для удаления
        redis_client: Клиент Redis (опционально)

    Returns:
        bool: True если успешно, False в случае ошибки
    """
    try:
        if not redis_client:
            redis_client = await get_redis_client()

        # Удаляем значение из Redis
        await redis_client.delete(key)

        logger.debug(f"Cache deleted: {key}")
        return True

    except RedisError as e:
        logger.error(
            f"Failed to delete cache: {key}", extra={"error": str(e), "error_type": type(e).__name__, "key": key}
        )
        return False


async def clear_cache(pattern: str = "*", redis_client: Optional[Redis] = None) -> bool:
    """
    Очистка кэша по шаблону.

    Args:
        pattern: Шаблон ключей для удаления
        redis_client: Клиент Redis (опционально)

    Returns:
        bool: True если успешно, False в случае ошибки
    """
    try:
        if not redis_client:
            redis_client = await get_redis_client()

        # Получаем все ключи по шаблону
        keys = await redis_client.keys(pattern)

        if not keys:
            logger.debug(f"No cache keys found for pattern: {pattern}")
            return True

        # Удаляем все найденные ключи
        await redis_client.delete(*keys)

        logger.info(f"Cache cleared for pattern: {pattern}", extra={"pattern": pattern, "keys_count": len(keys)})
        return True

    except RedisError as e:
        logger.error(
            f"Failed to clear cache for pattern: {pattern}",
            extra={"error": str(e), "error_type": type(e).__name__, "pattern": pattern},
        )
        return False


async def get_cache_stats(redis_client: Optional[Redis] = None) -> Dict[str, Any]:
    """
    Получение статистики кэша.

    Args:
        redis_client: Клиент Redis (опционально)

    Returns:
        Dict[str, Any]: Статистика кэша
    """
    try:
        if not redis_client:
            redis_client = await get_redis_client()

        # Получаем информацию о Redis
        info = await redis_client.info()

        # Формируем статистику
        stats = {
            "used_memory": info.get("used_memory_human", "0"),
            "connected_clients": info.get("connected_clients", 0),
            "total_keys": info.get("db0", {}).get("keys", 0),
            "uptime_days": info.get("uptime_in_days", 0),
            "last_save_time": info.get("last_save_time", 0),
            "role": info.get("role", "unknown"),
        }

        logger.debug("Cache stats retrieved")
        return stats

    except RedisError as e:
        logger.error("Failed to get cache stats", extra={"error": str(e), "error_type": type(e).__name__})
        return {}
