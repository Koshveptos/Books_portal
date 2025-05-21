import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.config import settings

# Создаем директорию для логов, если она не существует
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Настройка форматирования логов
log_format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s - " "[%(filename)s:%(lineno)d] - %(funcName)s()"
)

# Настройка файлового обработчика с ротацией
file_handler = RotatingFileHandler(
    filename=log_dir / "api.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(log_format)

# Настройка консольного обработчика
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)

# Создаем логгер
logger = logging.getLogger("books_portal")
logger.setLevel(settings.LOG_LEVEL)

# Добавляем обработчики
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Отключаем логирование от других библиотек
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("alembic").setLevel(logging.WARNING)


# Функция для логирования запросов
def log_request(request, response=None, error=None):
    """Логирование HTTP запросов с дополнительной информацией"""
    log_data = {
        "method": request.method,
        "url": str(request.url),
        "client": request.client.host if request.client else "Unknown",
        "user_agent": request.headers.get("user-agent", "Unknown"),
        "query_params": dict(request.query_params),
        "headers": dict(request.headers),
    }

    if response:
        log_data.update(
            {
                "status_code": response.status_code,
                "response_time": getattr(response, "response_time", None),
            }
        )

    if error:
        log_data.update(
            {
                "error": str(error),
                "error_type": type(error).__name__,
            }
        )

    if error:
        logger.error("Request failed", extra=log_data)
    else:
        logger.info("Request completed", extra=log_data)


# Функция для логирования ошибок базы данных
def log_db_error(error, operation, table=None, user_id=None):
    """Логирование ошибок базы данных"""
    log_data = {
        "operation": operation,
        "table": table,
        "user_id": user_id,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    logger.error("Database error", extra=log_data)


# Функция для логирования ошибок внешних API
def log_external_api_error(error, api_name, endpoint=None):
    """Логирование ошибок внешних API"""
    log_data = {
        "api_name": api_name,
        "endpoint": endpoint,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    logger.error("External API error", extra=log_data)


# Функция для логирования ошибок аутентификации
def log_auth_error(error, operation=None, user_id=None, action=None):
    """Логирование ошибок аутентификации и авторизации"""
    log_data = {
        "user_id": user_id,
        "action": action,
        "operation": operation,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    logger.error("Authentication error", extra=log_data)


# Функция для логирования информационных сообщений аутентификации
def log_auth_info(message, operation=None, user_id=None):
    """Логирование информационных сообщений аутентификации"""
    log_data = {
        "operation": operation,
        "user_id": user_id,
    }
    logger.info(message, extra=log_data)


# Функция для логирования предупреждений аутентификации
def log_auth_warning(message, operation=None, user_id=None):
    """Логирование предупреждений аутентификации"""
    log_data = {
        "operation": operation,
        "user_id": user_id,
    }
    logger.warning(message, extra=log_data)


# Функция для логирования ошибок валидации
def log_validation_error(error, model_name=None, field=None):
    """Логирование ошибок валидации данных"""
    log_data = {
        "model": model_name,
        "field": field,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    logger.warning("Validation error", extra=log_data)


# Функция для логирования ошибок кэширования
def log_cache_error(error, operation=None, key=None):
    """Логирование ошибок работы с кэшем"""
    log_data = {
        "operation": operation,
        "key": key,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    logger.error("Cache error", extra=log_data)


# Функция для логирования ошибок загрузки файлов
def log_file_error(error, file_name=None, operation=None):
    """Логирование ошибок работы с файлами"""
    log_data = {
        "file_name": file_name,
        "operation": operation,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    logger.error("File operation error", extra=log_data)


# Функция для логирования ошибок поиска
def log_search_error(error, query=None, filters=None):
    """Логирование ошибок поиска"""
    log_data = {
        "query": query,
        "filters": filters,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    logger.error("Search error", extra=log_data)


# Функция для логирования ошибок рекомендаций
def log_recommendation_error(error, user_id=None, context=None):
    """Логирование ошибок формирования рекомендаций"""
    log_data = {
        "user_id": user_id,
        "context": context,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    logger.error("Recommendation error", extra=log_data)


# Функция для логирования бизнес-логики
def log_business_error(error, operation=None, context=None):
    """Логирование ошибок бизнес-логики"""
    log_data = {
        "operation": operation,
        "context": context,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    logger.error("Business logic error", extra=log_data)


# Функция для логирования критических ошибок
def log_critical_error(error, component=None, context=None):
    """Логирование критических ошибок"""
    log_data = {
        "component": component,
        "context": context,
        "error": str(error),
        "error_type": type(error).__name__,
        "traceback": error.__traceback__,
    }
    logger.critical("Critical error", extra=log_data)


# Функция для логирования информационных сообщений
def log_info(message, context=None):
    """Логирование информационных сообщений"""
    log_data = {
        "context": context,
    }
    logger.info(message, extra=log_data)


# Функция для логирования предупреждений
def log_warning(message, context=None):
    """Логирование предупреждений"""
    log_data = {
        "context": context,
    }
    logger.warning(message, extra=log_data)


# Функция для логирования отладочной информации
def log_debug(message, context=None):
    """Логирование отладочной информации"""
    log_data = {
        "context": context,
    }
    logger.debug(message, extra=log_data)
