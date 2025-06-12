"""
Модуль с middleware для FastAPI приложения.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.exceptions import BookPortalException
from app.core.logger_config import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования HTTP запросов.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Обработка запроса с логированием.
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "client": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                },
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time

            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "process_time": process_time,
                    "client": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "error": str(e),
                },
            )
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware для обработки ошибок"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except BookPortalException as e:
            # Обрабатываем известные исключения приложения
            error_response = e.to_dict()
            if settings.ERROR_DETAILS_ENABLED and e.details:
                error_response["details"] = e.details
            if settings.ERROR_STACK_TRACE_ENABLED:
                error_response["stack_trace"] = str(e.__traceback__)

            logger.error(
                f"Business error: {e.message}",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "error_code": e.error_code,
                    "error_message": e.message,
                    "details": e.details,
                    "status_code": e.status_code,
                },
            )

            return Response(content=str(error_response), status_code=e.status_code, media_type="application/json")
        except Exception as e:
            # Обрабатываем неизвестные исключения
            logger.exception(
                f"Unhandled error: {str(e)}",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )

            error_response = {"error_code": "internal_error", "message": "Внутренняя ошибка сервера"}

            if settings.ERROR_DETAILS_ENABLED:
                error_response["details"] = {"error": str(e)}
            if settings.ERROR_STACK_TRACE_ENABLED:
                error_response["stack_trace"] = str(e.__traceback__)

            return Response(content=str(error_response), status_code=500, media_type="application/json")


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware для обработки таймаутов"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except TimeoutError:
            logger.error(
                f"Request timeout: {request.method} {request.url.path}",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "path": request.url.path,
                    "timeout": settings.ERROR_TIMEOUT,
                },
            )

            error_response = {"error_code": "request_timeout", "message": "Превышено время ожидания ответа"}

            if settings.ERROR_DETAILS_ENABLED:
                error_response["details"] = {"timeout": settings.ERROR_TIMEOUT}

            return Response(content=str(error_response), status_code=504, media_type="application/json")


def setup_middleware(app: ASGIApp) -> None:
    """
    Настройка middleware для приложения.

    Args:
        app: FastAPI приложение
    """
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(TimeoutMiddleware)
