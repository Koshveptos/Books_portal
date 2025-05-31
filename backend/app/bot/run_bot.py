import logging

from .bot import start_bot

logger = logging.getLogger(__name__)


async def run_bot():
    """Запуск бота"""
    try:
        logger.info("Starting Telegram bot...")
        await start_bot()
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {str(e)}")
        raise
