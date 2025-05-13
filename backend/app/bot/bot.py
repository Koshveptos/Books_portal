import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode

from bot.handlers.common import register_handlers
from bot.handlers.errors import register_error_handlers

# Создаем экземпляр бота и диспетчера для обработки команд
API_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

register_handlers(dp)
register_error_handlers(dp)


# Функция для запуска бота
async def start_bot():
    from aiogram import executor

    logging.info("Запуск телеграм бота...")
    await executor.start_polling(dp, skip_updates=True)
