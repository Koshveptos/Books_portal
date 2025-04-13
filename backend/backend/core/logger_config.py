import logging
import sys
from pathlib import Path

from loguru import logger

# Определяем путь к файлу логов относительно корня проекта
# BASE_DIR = Path(__file__).resolve().parent.parent.parent # Если logging_config.py в app/core/
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Если logging_config.py в app/
LOG_FILE = BASE_DIR / "logs" / "app.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)  # Создаем директорию logs, если её нет

# Убираем стандартный обработчик Loguru (который пишет в stderr)
logger.remove()

# Добавляем обработчик для записи в файл
logger.add(
    LOG_FILE,  # Путь к файлу
    level="INFO",  # Минимальный уровень для записи в файл (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    rotation="10 MB",  # Ротация логов при достижении 10 MB
    retention="7 days",  # Хранить файлы логов за последние 7 дней
    compression="zip",  # Сжимать старые логи в zip архивы
    # serialize=True,            #JSON ФОРМАТ, потом мб поставить
    enqueue=True,  # Асинхронная запись (важно для производительности веб-сервера)
    backtrace=True,  # Включать полный traceback при ошибках
    diagnose=True,  # Включать диагностику переменных при ошибках (может быть небезопасно в проде!)
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",  # Формат записи
    # serialize=True              # Опционально: записывать логи в формате JSON (удобно для систем сбора логов)
)

# Добавляем обработчик для вывода в консоль (например, для локальной разработки)
# Можно установить другой уровень, например DEBUG
logger.add(
    sys.stdout,  # Вывод в stdout (консоль)
    level="DEBUG",  # Уровень для консоли
    colorize=True,  # Цветной вывод
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)


# Перехват стандартных логов Python (если какие-то библиотеки используют logging)
# Это полезно, чтобы логи uvicorn и других библиотек тоже попадали в Loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Получаем соответствующий уровень Loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Находим вызывающий фрейм для корректного отображения имени файла и строки
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[InterceptHandler()], level=0)
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]  # Перехватываем логи доступа uvicorn
# Можно перехватить и другие логгеры по имени, если нужно
# logging.getLogger("sqlalchemy.engine").handlers = [InterceptHandler()]


# Экспортируем настроенный логгер для использования в других модулях
__all__ = ["logger"]
