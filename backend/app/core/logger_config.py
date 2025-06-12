"""
Конфигурация логирования.
"""

import logging
import logging.handlers
import os
import sys
from typing import Any, Dict, Optional

from app.core.config import settings


def setup_logger() -> logging.Logger:
    """Настройка логгера приложения."""
    # Создаем директорию для логов, если она не существует
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Создаем форматтер для логов
    formatter = logging.Formatter(fmt=settings.LOG_FORMAT, datefmt=settings.LOG_DATE_FORMAT)

    # Настраиваем файловый обработчик
    file_handler = logging.handlers.RotatingFileHandler(
        filename=settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # Настраиваем консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Создаем логгер
    logger = logging.getLogger("books_portal")
    logger.setLevel(settings.LOG_LEVEL)

    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Создаем глобальный логгер
logger = setup_logger()


def log_request(
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    process_time: float,
    client: Optional[str] = None,
    user_agent: Optional[str] = None,
    error: Optional[Exception] = None,
) -> None:
    """Логирование HTTP запроса."""
    log_data = {
        "request_id": request_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "process_time": process_time,
        "client": client,
        "user_agent": user_agent,
    }

    if error:
        log_data.update({"error": str(error), "error_type": type(error).__name__})
        logger.error(f"Request failed: {method} {path}", extra=log_data)
    else:
        logger.info(f"Request completed: {method} {path}", extra=log_data)


def log_error(
    error: Exception, error_type: str, context: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None
) -> None:
    """Логирование ошибки."""
    log_data = {
        "error_type": error_type,
        "error": str(error),
        "error_class": error.__class__.__name__,
        "error_module": error.__class__.__module__,
    }

    if context:
        log_data["context"] = context
    if request_id:
        log_data["request_id"] = request_id

    logger.error(f"{error_type} error: {str(error)}", extra=log_data, exc_info=True)


def log_critical_error(
    error: Exception, error_type: str, context: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None
) -> None:
    """Логирование критической ошибки."""
    log_data = {
        "error_type": error_type,
        "error": str(error),
        "error_class": error.__class__.__name__,
        "error_module": error.__class__.__module__,
        "stack_trace": getattr(error, "__traceback__", None),
    }

    if context:
        log_data["context"] = context
    if request_id:
        log_data["request_id"] = request_id

    logger.critical(f"Critical {error_type} error: {str(error)}", extra=log_data, exc_info=True)


def log_info(message: str, context: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> None:
    """Логирование информационного сообщения."""
    log_data = {}
    if context:
        log_data["context"] = context
    if request_id:
        log_data["request_id"] = request_id

    logger.info(message, extra=log_data)


def log_debug(message: str, context: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> None:
    """Логирование отладочного сообщения."""
    log_data = {}
    if context:
        log_data["context"] = context
    if request_id:
        log_data["request_id"] = request_id

    logger.debug(message, extra=log_data)


def log_warning(message: str, context: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> None:
    """Логирование предупреждения."""
    log_data = {}
    if context:
        log_data["context"] = context
    if request_id:
        log_data["request_id"] = request_id

    logger.warning(message, extra=log_data)


def log_db_error(error: Exception, operation: str = None, context: dict = None):
    """Логирование ошибок базы данных."""
    error_msg = f"Database error: {str(error)}"
    if operation:
        error_msg += f" Operation: {operation}"
    if context:
        error_msg += f" Context: {context}"

    logger.error(
        error_msg,
        exc_info=True,
        extra={
            "error_type": "database",
            "error_details": str(error),
            "operation": operation,
            "context": context,
            "error_class": error.__class__.__name__,
            "error_module": error.__class__.__module__,
        },
    )


def log_security_event(event_type: str, details: dict, context: dict = None):
    """Логирование событий безопасности."""
    log_data = {"event_type": event_type, "details": details}
    if context:
        log_data["context"] = context
    logger.warning(f"Security event: {event_type}", extra=log_data)


def log_auth_error(error: Exception, operation: str = None, context: dict = None):
    """Логирование ошибок аутентификации."""
    error_msg = f"Authentication error: {str(error)}"
    if operation:
        error_msg += f" Operation: {operation}"
    if context:
        error_msg += f" Context: {context}"

    logger.error(
        error_msg,
        exc_info=True,
        extra={
            "error_type": "authentication",
            "error_details": str(error),
            "operation": operation,
            "context": context,
            "error_class": error.__class__.__name__,
            "error_module": error.__class__.__module__,
        },
    )


def log_auth_info(message: str, context: dict = None):
    """Логирование информационных сообщений аутентификации."""
    log_data = {}
    if context:
        log_data["context"] = context
    logger.info(f"Authentication info: {message}", extra=log_data)


def log_auth_warning(message: str, context: dict = None):
    """Логирование предупреждений аутентификации."""
    log_data = {}
    if context:
        log_data["context"] = context
    logger.warning(f"Authentication warning: {message}", extra=log_data)


def log_auth_debug(message: str, context: dict = None):
    """Логирование отладочных сообщений аутентификации."""
    log_data = {}
    if context:
        log_data["context"] = context
    logger.debug(f"Authentication debug: {message}", extra=log_data)


def log_auth_success(message: str, context: dict = None):
    """Логирование успешных операций аутентификации."""
    log_data = {}
    if context:
        log_data["context"] = context
    logger.info(f"Authentication success: {message}", extra=log_data)


def log_auth_failure(message: str, context: dict = None):
    """Логирование неудачных операций аутентификации."""
    log_data = {}
    if context:
        log_data["context"] = context
    logger.warning(f"Authentication failure: {message}", extra=log_data)


def log_auth_attempt(message: str, context: dict = None):
    """Логирование попыток аутентификации."""
    log_data = {}
    if context:
        log_data["context"] = context
    logger.info(f"Authentication attempt: {message}", extra=log_data)


def log_validation_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Логирование ошибок валидации."""
    log_data = {
        "error_type": "validation",
        "error": str(error),
        "error_class": error.__class__.__name__,
        "error_module": error.__class__.__module__,
    }

    if context:
        log_data["context"] = context

    logger.error(f"Validation error: {str(error)}", extra=log_data, exc_info=True)


def log_cache_error(error: Exception, context: dict = None):
    """Логирование ошибок кэширования."""
    error_msg = f"Cache error: {str(error)}"
    if context:
        error_msg += f" Context: {context}"

    logger.error(
        error_msg,
        exc_info=True,
        extra={
            "error_type": "cache",
            "error_details": str(error),
            "context": context,
            "error_class": error.__class__.__name__,
            "error_module": error.__class__.__module__,
        },
    )


def log_business_error(message: str, context: dict = None):
    """Логирование бизнес-ошибок (ошибки уровня приложения, не критические)."""
    log_data = {}
    if context:
        log_data["context"] = context
    logger.warning(f"Business error: {message}", extra=log_data)


def log_performance(operation: str, duration: float, context: dict = None):
    """Логирование производительности (время выполнения операций)."""
    log_data = {"operation": operation, "duration": duration}
    if context:
        log_data["context"] = context
    logger.info(f"Performance: {operation} took {duration:.4f} seconds", extra=log_data)
