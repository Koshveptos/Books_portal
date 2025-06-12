"""
Модуль для запуска и остановки телеграм бота.
"""

import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.bot import dp
from app.bot.config import BOT_TOKEN
from app.core.logger_config import logger


async def start_bot():
    """
    Запуск телеграм бота.
    """
    try:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        # Запускаем бота в отдельной задаче
        asyncio.create_task(dp.start_polling(bot))
        logger.info("Telegram bot started successfully")
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {str(e)}")
        raise


async def stop_bot():
    """
    Остановка телеграм бота.
    """
    try:
        await dp.stop_polling()
        logger.info("Telegram bot stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop Telegram bot: {str(e)}")
        raise
