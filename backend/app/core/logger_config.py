import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Создаем директорию для логов, если она не существует
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Настраиваем формат логов
log_format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d] - %(funcName)s()"
)

# Настраиваем файловый обработчик
file_handler = RotatingFileHandler("logs/api.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")  # 10MB
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)

# Настраиваем консольный обработчик
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(log_format)

# Создаем логгер
logger = logging.getLogger("books_portal")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Устанавливаем уровень логирования для других библиотек
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("alembic").setLevel(logging.WARNING)


def log_db_error(error: Exception, context: dict = None):
    """Логирование ошибок базы данных"""
    error_msg = f"Database error: {str(error)}"
    if context:
        error_msg += f" Context: {context}"
    logger.error(
        error_msg, exc_info=True, extra={"error_type": "database", "error_details": str(error), "context": context}
    )


def log_cache_error(error: Exception, context: dict = None):
    """Логирование ошибок кэша"""
    error_msg = f"Cache error: {str(error)}"
    if context:
        error_msg += f" Context: {context}"
    logger.error(
        error_msg, exc_info=True, extra={"error_type": "cache", "error_details": str(error), "context": context}
    )


def log_recommendation_error(error: Exception, context: dict = None):
    """Логирование ошибок рекомендаций"""
    error_msg = f"Recommendation error: {str(error)}"
    if context:
        error_msg += f" Context: {context}"
    logger.error(
        error_msg,
        exc_info=True,
        extra={"error_type": "recommendation", "error_details": str(error), "context": context},
    )


def log_critical_error(error: Exception, context: dict = None):
    """Логирование критических ошибок"""
    error_msg = f"Critical error: {str(error)}"
    if context:
        error_msg += f" Context: {context}"
    logger.critical(
        error_msg, exc_info=True, extra={"error_type": "critical", "error_details": str(error), "context": context}
    )


def log_info(message: str, context: dict = None):
    """Логирование информационных сообщений"""
    if context:
        message += f" Context: {context}"
    logger.info(message, extra={"context": context})


def log_debug(message: str, context: dict = None):
    """Логирование отладочных сообщений"""
    if context:
        message += f" Context: {context}"
    logger.debug(message, extra={"context": context})


def log_warning(message: str, context: dict = None):
    """Логирование предупреждений"""
    if context:
        message += f" Context: {context}"
    logger.warning(message, extra={"context": context})


def log_error(message: str, context: dict = None):
    """Логирование ошибок"""
    if context:
        message += f" Context: {context}"
    logger.error(message, exc_info=True, extra={"context": context})


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
