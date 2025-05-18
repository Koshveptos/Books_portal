import redis.asyncio as redis
from core.config import settings
from core.logger_config import logger

redis_client = None


async def init_redis():
    global redis_client
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
        await redis_client.ping()
        logger.info("Redis client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {e}")
        raise


async def get_redis():
    if redis_client is None:
        await init_redis()
    return redis_client
