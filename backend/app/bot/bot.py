"""
Основной модуль телеграм бота.
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.logger_config import logger

from ..core.config import settings
from .handlers import register_handlers
from .middlewares import register_middlewares

# Инициализация бота и диспетчера
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Создаем диспетчер с хранилищем состояний
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрируем обработчики
register_handlers(dp)

logger.info("Telegram bot handlers registered")


async def start_bot():
    """Запуск бота"""
    try:
        logger.info("Starting Telegram bot...")

        # Регистрация обработчиков и middleware
        register_middlewares(dp)

        # Запуск бота
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Error starting Telegram bot: {str(e)}")
        raise
