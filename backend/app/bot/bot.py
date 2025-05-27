import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from ..core.config import settings
from .handlers import register_handlers
from .middlewares import register_middlewares

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def start_bot():
    """Запуск бота"""
    try:
        logger.info("Starting Telegram bot...")

        # Регистрация обработчиков и middleware
        register_handlers(dp)
        register_middlewares(dp)

        # Запуск бота
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Error starting Telegram bot: {str(e)}")
        raise
