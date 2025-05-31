import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import Dispatcher
from aiogram.types import Message

logger = logging.getLogger(__name__)


def register_middlewares(dp: Dispatcher):
    """Регистрация всех middleware"""

    # Регистрируем middleware для логирования
    dp.message.middleware(logging_middleware)


async def logging_middleware(
    handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]], event: Message, data: Dict[str, Any]
) -> Any:
    """
    Middleware для логирования всех входящих сообщений
    """
    logger.info(f"Получено сообщение от пользователя {event.from_user.id}: {event.text}")
    return await handler(event, data)
