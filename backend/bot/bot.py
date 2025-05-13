# import logging

# from aiogram import Bot, Dispatcher
# from aiogram.types import Update
# from fastapi import FastAPI

# from app.core.config import settings

# # Настройка логирования
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Инициализация бота
# bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
# dp = Dispatcher(bot)

# # Подключаем обработчики
# from bot.handlers.common import register_handlers
# from bot.handlers.errors import register_error_handlers

# register_handlers(dp)
# register_error_handlers(dp)


# # Функция для настройки вебхуков
# async def setup_webhook(app: FastAPI):
#     logger.info("Setting up webhook...")
#     await bot.set_webhook(settings.WEBHOOK_URL)
#     logger.info(f"Webhook set to {settings.WEBHOOK_URL}")


# # Функция для обработки входящих обновлений
# async def process_update(update: dict):
#     telegram_update = Update(**update)
#     await dp.process_update(telegram_update)


# # Очистка вебхуков при завершении
# async def on_shutdown(app: FastAPI):
#     logger.info("Shutting down, deleting webhook...")
#     await bot.delete_webhook()
