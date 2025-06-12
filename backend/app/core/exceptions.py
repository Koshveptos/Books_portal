from typing import Any, Dict, Optional

from fastapi import status


class BookPortalException(Exception):
    """Базовое исключение для всех ошибок приложения Books Portal"""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    message: str = "Внутренняя ошибка сервера"
    details: Optional[Dict[str, Any]] = None

    def __init__(
        self, message: str = None, status_code: int = None, error_code: str = None, details: Dict[str, Any] = None
    ):
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        if details:
            self.details = details
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует исключение в словарь для ответа API"""
        response = {"error_code": self.error_code, "message": self.message}
        if self.details:
            response["details"] = self.details
        return response

    def with_details(self, details: Dict[str, Any]) -> "BookPortalException":
        """Добавляет детали к исключению"""
        self.details = details
        return self

    def with_message(self, message: str) -> "BookPortalException":
        """Обновляет сообщение исключения"""
        self.message = message
        return self

    def with_status_code(self, status_code: int) -> "BookPortalException":
        """Обновляет код статуса исключения"""
        self.status_code = status_code
        return self

    def with_error_code(self, error_code: str) -> "BookPortalException":
        """Обновляет код ошибки исключения"""
        self.error_code = error_code
        return self

    def __str__(self) -> str:
        """Строковое представление исключения"""
        result = f"{self.error_code}: {self.message}"
        if self.details:
            result += f" (Details: {self.details})"
        return result


# Ошибки аутентификации и авторизации
class AuthenticationException(BookPortalException):
    """Ошибка аутентификации"""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"
    message = "Ошибка аутентификации"


class CredentialsException(BookPortalException):
    """Недействительные учетные данные"""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "invalid_credentials"
    message = "Недействительные учетные данные"


class TokenExpiredException(BookPortalException):
    """Срок действия токена истек"""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "token_expired"
    message = "Срок действия токена истек"


class UserDeactivatedException(BookPortalException):
    """Пользователь деактивирован"""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "user_deactivated"
    message = "Пользователь деактивирован"


class PermissionDeniedException(BookPortalException):
    """Ошибка прав доступа"""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "permission_denied"
    message = "Недостаточно прав для выполнения операции"


# Ошибки, связанные с пользователями
class UserNotFoundException(BookPortalException):
    """Пользователь не найден"""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "user_not_found"
    message = "Пользователь не найден"


class UserAlreadyExistsException(BookPortalException):
    """Пользователь уже существует"""

    status_code = status.HTTP_409_CONFLICT
    error_code = "user_already_exists"
    message = "Пользователь с таким email уже существует"


class InvalidUserDataException(BookPortalException):
    """Некорректные данные пользователя"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_user_data"
    message = "Некорректные данные пользователя"


# Ошибки, связанные с книгами
class BookNotFoundException(BookPortalException):
    """Книга не найдена"""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "book_not_found"
    message = "Книга не найдена"


class InvalidBookDataException(BookPortalException):
    """Некорректные данные книги"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_book_data"
    message = "Некорректные данные книги"


# Ошибки, связанные с авторами
class AuthorNotFoundException(BookPortalException):
    """Автор не найден"""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "author_not_found"
    message = "Автор не найден"


class InvalidAuthorDataException(BookPortalException):
    """Некорректные данные автора"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_author_data"
    message = "Некорректные данные автора"


# Ошибки, связанные с категориями
class CategoryNotFoundException(BookPortalException):
    """Категория не найдена"""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "category_not_found"
    message = "Категория не найдена"


class InvalidCategoryDataException(BookPortalException):
    """Некорректные данные категории"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_category_data"
    message = "Некорректные данные категории"


# Ошибки, связанные с тегами
class TagNotFoundException(BookPortalException):
    """Тег не найден"""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "tag_not_found"
    message = "Тег не найден"


class InvalidTagDataException(BookPortalException):
    """Некорректные данные тега"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_tag_data"
    message = "Некорректные данные тега"


# Ошибки, связанные с запросами
class ValidationException(BookPortalException):
    """Ошибка валидации"""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"
    message = "Ошибка валидации данных"


# Ошибки доступа к БД
class DatabaseException(BookPortalException):
    """Ошибка базы данных"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "database_error"
    message = "Ошибка базы данных"


# Ошибки, связанные с рейтингами
class RatingNotFoundException(BookPortalException):
    """Рейтинг не найден"""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "rating_not_found"
    message = "Рейтинг не найден"


class InvalidRatingValueException(BookPortalException):
    """Некорректное значение рейтинга"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_rating_value"
    message = "Значение рейтинга должно быть от 1 до 5"


# Ошибки, связанные с лайками
class LikeNotFoundException(BookPortalException):
    """Лайк не найден"""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "like_not_found"
    message = "Лайк не найден"


class LikeAlreadyExistsException(BookPortalException):
    """Лайк уже существует"""

    status_code = status.HTTP_409_CONFLICT
    error_code = "like_already_exists"
    message = "Лайк уже существует"


# Ошибки, связанные с избранным
class FavoriteNotFoundException(BookPortalException):
    """Избранное не найдено"""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "favorite_not_found"
    message = "Избранное не найдено"


class FavoriteAlreadyExistsException(BookPortalException):
    """Избранное уже существует"""

    status_code = status.HTTP_409_CONFLICT
    error_code = "favorite_already_exists"
    message = "Избранное уже существует"


# Ошибки, связанные с поиском
class SearchException(BookPortalException):
    """Ошибка поиска"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "search_error"
    message = "Ошибка при выполнении поиска"


class InvalidSearchQueryException(BookPortalException):
    """Некорректный поисковый запрос"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_search_query"
    message = "Некорректный поисковый запрос"


# Ошибки, связанные с рекомендациями
class RecommendationException(BookPortalException):
    """Ошибка рекомендаций"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "recommendation_error"
    message = "Ошибка при формировании рекомендаций"


class NotEnoughDataForRecommendationException(BookPortalException):
    """Недостаточно данных для рекомендаций"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "not_enough_data"
    message = "Недостаточно данных для формирования рекомендаций"


# Ошибки, связанные с файлами
class FileUploadException(BookPortalException):
    """Ошибка загрузки файла"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "file_upload_error"
    message = "Ошибка при загрузке файла"


class InvalidFileTypeException(BookPortalException):
    """Неподдерживаемый тип файла"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_file_type"
    message = "Неподдерживаемый тип файла"


class FileSizeExceededException(BookPortalException):
    """Превышен размер файла"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "file_size_exceeded"
    message = "Превышен максимально допустимый размер файла"


# Ошибки, связанные с кэшированием
class CacheException(BookPortalException):
    """Ошибка кэширования"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "cache_error"
    message = "Ошибка при работе с кэшем"


# Ошибки, связанные с внешними API
class ExternalAPIException(BookPortalException):
    """Ошибка внешнего API"""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "external_api_error"
    message = "Ошибка при обращении к внешнему API"


class ExternalAPITimeoutException(BookPortalException):
    """Таймаут внешнего API"""

    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    error_code = "external_api_timeout"
    message = "Превышено время ожидания ответа от внешнего API"


class ResourceNotFoundException(BookPortalException):
    """Ресурс не найден"""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "resource_not_found"
    message = "Запрашиваемый ресурс не найден"


# Ошибки, связанные с сессиями базы данных
class DatabaseSessionException(BookPortalException):
    """Ошибка сессии базы данных"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "database_session_error"
    message = "Ошибка при работе с сессией базы данных"


class DatabaseConnectionException(BookPortalException):
    """Ошибка подключения к базе данных"""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "database_connection_error"
    message = "Ошибка подключения к базе данных"


class DatabaseInitializationException(BookPortalException):
    """Ошибка инициализации базы данных"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "database_initialization_error"
    message = "Ошибка при инициализации базы данных"


class DatabaseTransactionException(BookPortalException):
    """Ошибка транзакции базы данных"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "database_transaction_error"
    message = "Ошибка при выполнении транзакции базы данных"
