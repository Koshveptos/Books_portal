import logging
from typing import Any, Dict

import aiohttp

logger = logging.getLogger(__name__)


class BooksPortalAPI:
    """Класс для работы с API книжного портала"""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.session = None
        logger.info(f"Initialized API with base URL: {self.base_url}")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Выполнить запрос к API"""
        if not self.session:
            raise RuntimeError("API client not initialized. Use 'async with' context manager.")

        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 404:
                    return None

                data = await response.json()

                if response.status >= 400:
                    error_msg = data.get("message", "Unknown error")
                    raise Exception(f"API error: {error_msg}")

                return data
        except aiohttp.ClientError as e:
            raise Exception(f"Network error: {str(e)}")

    async def search_books(self, query: str, page: int = 1, limit: int = 10) -> dict:
        """Поиск книг"""
        params = {"q": query, "page": page, "limit": limit}
        books = await self._make_request("GET", "/search", params=params)

        # Преобразуем список книг в формат с пагинацией
        if isinstance(books, list):
            return {"items": books, "total": len(books), "page": page, "size": limit}
        return books

    async def get_catalog(self, page: int = 1, limit: int = 10) -> dict:
        """Получить каталог книг"""
        params = {"page": page, "limit": limit}
        return await self._make_request("GET", "/books", params=params)

    async def get_book_details(self, book_id: int) -> dict:
        """Получить детальную информацию о книге"""
        return await self._make_request("GET", f"/books/{book_id}")

    async def get_book_authors(self, book_id: int) -> list:
        """Получить список авторов книги"""
        return await self._make_request("GET", f"/books/{book_id}/authors")

    async def get_similar_books(self, book_id: int) -> list:
        """Получить список похожих книг"""
        return await self._make_request("GET", f"/books/{book_id}/similar")

    async def get_user_info(self, telegram_id: int) -> dict:
        """Получить информацию о пользователе"""
        return await self._make_request("GET", f"/users/telegram/{telegram_id}")

    async def get_user_books(self, telegram_id: int) -> list:
        """Получить список книг пользователя"""
        return await self._make_request("GET", f"/users/telegram/{telegram_id}/books")

    async def get_user_recommendations(self, telegram_id: int) -> list:
        """Получить рекомендации для пользователя"""
        return await self._make_request("GET", f"/users/telegram/{telegram_id}/recommendations")

    async def get_user_profile(self) -> Dict:
        """Получение профиля пользователя"""
        return await self._make_request("GET", "/users/profile")

    async def update_user_profile(self, data: Dict) -> Dict:
        """Обновление профиля пользователя"""
        return await self._make_request("PUT", "/users/profile", data=data)

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Авторизация пользователя"""
        try:
            data = {"username": email, "password": password}  # API ожидает username, а не email
            logger.info(f"Attempting login for user: {email}")
            response = await self._make_request(method="POST", endpoint="/auth/jwt/login", data=data)
            logger.info("Login successful")
            return response
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise ValueError(f"Ошибка авторизации: {str(e)}")

    async def link_telegram(self, user_id: int, telegram_id: int, token: str) -> Dict[str, Any]:
        """Привязка Telegram к аккаунту"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            data = {"telegram_id": telegram_id}

            logger.info(f"Attempting to link Telegram ID {telegram_id} to user {user_id}")
            response = await self._make_request(
                method="POST", endpoint="/users/me/telegram", data=data, headers=headers
            )
            logger.info("Telegram linking successful")
            return response
        except Exception as e:
            logger.error(f"Telegram linking failed: {str(e)}")
            raise ValueError(f"Ошибка привязки Telegram: {str(e)}")

    async def rate_book(self, book_id: int, rating: int) -> Dict:
        """Оценка книги"""
        data = {"rating": rating}
        return await self._make_request("POST", f"/books/{book_id}/rate", data=data)

    async def toggle_favorite(self, book_id: int) -> Dict:
        """Добавление/удаление книги из избранного"""
        return await self._make_request("POST", f"/books/{book_id}/favorite")
