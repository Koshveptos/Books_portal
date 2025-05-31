"""
Нагрузочное тестирование с помощью Locust
"""

import logging
import random
import uuid
from typing import Dict, Optional

import requests
from gevent import sleep, spawn
from gevent.event import Event
from locust import HttpUser, between, events, tag, task

logger = logging.getLogger(__name__)

# Глобальные переменные для хранения данных супер-администратора
SUPER_ADMIN_TOKEN = None
SUPER_ADMIN_HEADERS = None
SUPER_ADMIN_ID = None
SUPER_ADMIN_READY = Event()

# Данные тестового администратора
TEST_ADMIN_EMAIL = "book_owner_f51fea79@example.com"
TEST_ADMIN_PASSWORD = "Test1234!"

# Настройки тестирования
USERS_COUNT = 50  # Общее количество пользователей
SPAWN_RATE = 5  # Пользователей в секунду (уменьшено с 10)
WAIT_TIME_MIN = 1  # Минимальное время ожидания между запросами
WAIT_TIME_MAX = 5  # Максимальное время ожидания между запросами


class SuperAdminClient:
    """Клиент для инициализации супер-администратора"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30  # Увеличиваем таймаут для запросов

    def post(self, path: str, **kwargs) -> requests.Response:
        """Отправка POST запроса"""
        return self.session.post(f"{self.base_url}{path}", **kwargs)

    def get(self, path: str, **kwargs) -> requests.Response:
        """Отправка GET запроса"""
        return self.session.get(f"{self.base_url}{path}", **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        """Отправка PATCH запроса"""
        return self.session.patch(f"{self.base_url}{path}", **kwargs)


def init_super_admin():
    """Инициализация супер-администратора"""
    global SUPER_ADMIN_TOKEN, SUPER_ADMIN_HEADERS, SUPER_ADMIN_ID, SUPER_ADMIN_READY

    try:
        # Создаем клиент для работы с API
        client = SuperAdminClient()

        # Пробуем войти как тестовый администратор
        login_response = client.post(
            "/auth/jwt/login",
            data={"username": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if login_response.status_code == 200:
            SUPER_ADMIN_TOKEN = login_response.json()["access_token"]
            SUPER_ADMIN_HEADERS = {"Authorization": f"Bearer {SUPER_ADMIN_TOKEN}", "Content-Type": "application/json"}
            # Получаем ID администратора
            profile_response = client.get("/users/me", headers=SUPER_ADMIN_HEADERS)
            if profile_response.status_code == 200:
                SUPER_ADMIN_ID = profile_response.json()["id"]
                SUPER_ADMIN_READY.set()
                logger.info("Super admin is ready")
                return True
            else:
                logger.error(f"Failed to get admin profile: {profile_response.text}")
        else:
            logger.error(f"Failed to login as admin: {login_response.text}")
    except Exception as e:
        logger.error(f"Error in init_super_admin: {str(e)}")
    return False


class SuperAdmin(HttpUser):
    """Супер-администратор для управления правами пользователей"""

    abstract = True
    host = "http://localhost:8000"
    wait_time = between(1, 3)

    def on_start(self):
        """Действия при старте супер-администратора"""
        if not SUPER_ADMIN_READY.is_set():
            if not init_super_admin():
                self.environment.runner.quit()

    def on_stop(self):
        """Действия при остановке супер-администратора"""
        global SUPER_ADMIN_TOKEN, SUPER_ADMIN_HEADERS, SUPER_ADMIN_ID, SUPER_ADMIN_READY
        try:
            if SUPER_ADMIN_TOKEN:
                # Выход из системы
                self.client.post("/auth/jwt/logout", headers=SUPER_ADMIN_HEADERS)
        except Exception as e:
            logger.error(f"Error in super admin on_stop: {str(e)}")
        finally:
            SUPER_ADMIN_TOKEN = None
            SUPER_ADMIN_HEADERS = None
            SUPER_ADMIN_ID = None
            SUPER_ADMIN_READY.clear()


class BaseUser(HttpUser):
    """Базовый класс для всех пользователей"""

    abstract = True
    host = "http://localhost:8000"
    wait_time = between(WAIT_TIME_MIN, WAIT_TIME_MAX)
    token: Optional[str] = None
    headers: Dict[str, str] = {}
    user_id: Optional[int] = None
    email: Optional[str] = None

    def on_start(self):
        """Действия при старте пользователя"""
        try:
            # Ждем готовности супер-администратора
            if not SUPER_ADMIN_READY.wait(timeout=30):
                logger.error("Timeout waiting for super admin")
                self.environment.runner.quit()
                return

            # Добавляем задержку перед регистрацией
            sleep(random.uniform(0.1, 0.5))

            # Регистрация пользователя
            self.email = f"test_user_{uuid.uuid4()}@example.com"
            password = "Test1234!"

            register_response = self.client.post(
                "/auth/register",
                json={
                    "email": self.email,
                    "password": password,
                    "is_active": True,
                    "is_superuser": False,
                    "is_verified": True,
                },
                timeout=30,  # Увеличиваем таймаут для регистрации
            )

            if register_response.status_code != 201:
                logger.error(f"Failed to register user: {register_response.text}")
                self.environment.runner.quit()
                return

            # Добавляем задержку перед логином
            sleep(random.uniform(0.1, 0.3))

            # Получение токена
            login_response = self.client.post(
                "/auth/jwt/login",
                data={"username": self.email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,  # Увеличиваем таймаут для логина
            )

            if login_response.status_code == 200:
                self.token = login_response.json()["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
                # Получаем ID пользователя
                profile_response = self.client.get("/users/me", headers=self.headers, timeout=30)
                if profile_response.status_code == 200:
                    self.user_id = profile_response.json()["id"]
                    logger.info(f"User {self.email} successfully registered and logged in")
                else:
                    logger.error(f"Failed to get user profile: {profile_response.text}")
                    self.environment.runner.quit()
            else:
                logger.error(f"Failed to login user: {login_response.text}")
                self.environment.runner.quit()
        except Exception as e:
            logger.error(f"Error in on_start: {str(e)}")
            self.environment.runner.quit()

    def on_stop(self):
        """Действия при остановке пользователя"""
        try:
            if self.token:
                # Выход из системы
                self.client.post("/auth/jwt/logout", headers=self.headers)
        except Exception as e:
            logger.error(f"Error in on_stop: {str(e)}")
        finally:
            self.token = None
            self.headers = {}
            self.user_id = None
            self.email = None


class BooksPortalUser(BaseUser):
    """Обычный пользователь для нагрузочного тестирования"""

    weight = 3  # Больше обычных пользователей

    @task(5)  # Увеличено с 3
    @tag("read")
    def get_books(self):
        """Получение списка книг"""
        if not self.token:
            return
        self.client.get("/books/", headers=self.headers)

    @task(4)  # Увеличено с 2
    @tag("read")
    def get_book_details(self):
        """Получение детальной информации о книге"""
        if not self.token:
            return
        try:
            response = self.client.get("/books/", headers=self.headers)
            if response.status_code == 200:
                books = response.json()
                if books:
                    book = random.choice(books)
                    self.client.get(f"/books/{book['id']}", headers=self.headers)
        except Exception as e:
            logger.error(f"Error in get_book_details: {str(e)}")

    @task(3)  # Увеличено с 1
    @tag("read")
    def search_books(self):
        """Поиск книг"""
        if not self.token:
            return
        search_terms = [
            "python",
            "java",
            "database",
            "web",
            "programming",
            "fiction",
            "science",
            "history",
            "art",
            "math",
        ]
        query = random.choice(search_terms)
        self.client.get(f"/search/?q={query}&limit=10", headers=self.headers)

    @task(2)  # Увеличено с 1
    @tag("read")
    def get_user_profile(self):
        """Получение профиля пользователя"""
        if not self.token:
            return
        self.client.get("/users/me", headers=self.headers)

    @task(2)  # Увеличено с 1
    @tag("write")
    def rate_book(self):
        """Оценка книги"""
        if not self.token:
            return
        try:
            response = self.client.get("/books/", headers=self.headers)
            if response.status_code == 200:
                books = response.json()
                if books:
                    book = random.choice(books)
                    rating_data = {"rating": random.randint(1, 5), "comment": f"Test rating {uuid.uuid4().hex[:8]}"}
                    self.client.post(f"/ratings/{book['id']}", json=rating_data, headers=self.headers)
        except Exception as e:
            logger.error(f"Error in rate_book: {str(e)}")

    @task(1)
    @tag("read")
    def get_book_comments(self):
        """Получение комментариев к книге"""
        if not self.token:
            return
        try:
            response = self.client.get("/books/", headers=self.headers)
            if response.status_code == 200:
                books = response.json()
                if books:
                    book = random.choice(books)
                    self.client.get(f"/books/{book['id']}/comments", headers=self.headers)
        except Exception as e:
            logger.error(f"Error in get_book_comments: {str(e)}")

    @task(1)
    @tag("write")
    def add_book_comment(self):
        """Добавление комментария к книге"""
        if not self.token:
            return
        try:
            response = self.client.get("/books/", headers=self.headers)
            if response.status_code == 200:
                books = response.json()
                if books:
                    book = random.choice(books)
                    comment_data = {"text": f"Test comment {uuid.uuid4().hex[:8]}"}
                    self.client.post(f"/books/{book['id']}/comments", json=comment_data, headers=self.headers)
        except Exception as e:
            logger.error(f"Error in add_book_comment: {str(e)}")


class AdminUser(BaseUser):
    """Администратор для нагрузочного тестирования"""

    weight = 1
    is_admin = False  # Флаг для отслеживания статуса прав

    def on_start(self):
        """Действия при старте администратора"""
        super().on_start()
        if self.token and self.user_id and SUPER_ADMIN_HEADERS:
            try:
                # Устанавливаем права администратора через супер-администратора
                client = SuperAdminClient()
                response = client.patch(
                    f"/users/{self.user_id}/status", json={"is_superuser": True}, headers=SUPER_ADMIN_HEADERS
                )
                if response.status_code != 200:
                    logger.error(f"Failed to set admin rights: {response.text}")
                    self.environment.runner.quit()
                    return

                # Обновляем токен после изменения прав
                login_response = self.client.post(
                    "/auth/jwt/login",
                    data={"username": self.email, "password": "Test1234!"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if login_response.status_code == 200:
                    self.token = login_response.json()["access_token"]
                    self.headers["Authorization"] = f"Bearer {self.token}"
                    # Проверяем, что права действительно установлены
                    profile_response = self.client.get("/users/me", headers=self.headers)
                    if profile_response.status_code == 200:
                        user_data = profile_response.json()
                        if user_data.get("is_superuser"):
                            self.is_admin = True
                            logger.info(f"Admin rights successfully set for user {self.email}")
                        else:
                            logger.error("Admin rights not set properly")
                            self.environment.runner.quit()
                    else:
                        logger.error(f"Failed to verify admin rights: {profile_response.text}")
                        self.environment.runner.quit()
                else:
                    logger.error(f"Failed to update token after setting admin rights: {login_response.text}")
                    self.environment.runner.quit()
            except Exception as e:
                logger.error(f"Error setting admin rights: {str(e)}")
                self.environment.runner.quit()

    @task(3)  # Увеличено с 1
    @tag("admin")
    def create_author(self):
        """Создание нового автора"""
        if not self.token or not self.is_admin:
            return
        try:
            author_data = {
                "name": f"Test Author {uuid.uuid4().hex[:8]}",
                "biography": f"Test biography for {uuid.uuid4().hex[:8]}",
            }
            self.client.post("/authors/", json=author_data, headers=self.headers)
        except Exception as e:
            logger.error(f"Error in create_author: {str(e)}")

    @task(3)  # Увеличено с 1
    @tag("admin")
    def create_category(self):
        """Создание новой категории"""
        if not self.token or not self.is_admin:
            return
        try:
            category_data = {
                "name_categories": f"Category {uuid.uuid4().hex[:8]}",
                "description": f"Test category description {uuid.uuid4().hex[:8]}",
            }
            self.client.post("/categories/", json=category_data, headers=self.headers)
        except Exception as e:
            logger.error(f"Error in create_category: {str(e)}")

    @task(3)  # Увеличено с 1
    @tag("admin")
    def create_tag(self):
        """Создание нового тега"""
        if not self.token or not self.is_admin:
            return
        try:
            tag_data = {
                "name_tag": f"Tag {uuid.uuid4().hex[:8]}",
                "description": f"Test tag description {uuid.uuid4().hex[:8]}",
            }
            self.client.post("/tags/", json=tag_data, headers=self.headers)
        except Exception as e:
            logger.error(f"Error in create_tag: {str(e)}")

    @task(2)  # Увеличено с 1
    @tag("admin")
    def create_book(self):
        """Создание новой книги"""
        if not self.token or not self.is_admin:
            return
        try:
            # Получаем необходимые данные
            authors = self.client.get("/authors/", headers=self.headers).json()
            categories = self.client.get("/categories/", headers=self.headers).json()
            tags = self.client.get("/tags/", headers=self.headers).json()

            if not all([authors, categories, tags]):
                return

            book_data = {
                "title": f"Test Book {uuid.uuid4().hex[:8]}",
                "description": f"Test description for load testing {uuid.uuid4().hex[:8]}",
                "language": random.choice(["ru", "en"]),
                "publication_year": random.randint(2000, 2024),
                "isbn": f"978-{random.randint(1000000000, 9999999999)}",
                "publisher": f"Test Publisher {uuid.uuid4().hex[:8]}",
                "file_url": f"test_{uuid.uuid4().hex[:8]}.pdf",
                "authors": [random.choice(authors)["id"]],
                "categories": [random.choice(categories)["id"]],
                "tags": [random.choice(tags)["id"]],
            }
            self.client.post("/books/", json=book_data, headers=self.headers)
        except Exception as e:
            logger.error(f"Error in create_book: {str(e)}")

    @task(2)
    @tag("admin")
    def manage_users(self):
        """Управление пользователями"""
        if not self.token or not self.is_admin:
            return
        try:
            # Получаем список пользователей
            response = self.client.get("/users/", headers=self.headers)
            if response.status_code == 200:
                users = response.json()
                if users:
                    user = random.choice(users)
                    # Обновляем статус пользователя
                    update_data = {"is_active": random.choice([True, False])}
                    self.client.patch(f"/users/{user['id']}/status", json=update_data, headers=self.headers)
        except Exception as e:
            logger.error(f"Error in manage_users: {str(e)}")


class ModeratorUser(BaseUser):
    """Модератор для нагрузочного тестирования"""

    weight = 2
    is_moderator = False  # Флаг для отслеживания статуса прав

    def on_start(self):
        """Действия при старте модератора"""
        super().on_start()
        if self.token and self.user_id and SUPER_ADMIN_HEADERS:
            try:
                # Устанавливаем права модератора через супер-администратора
                client = SuperAdminClient()
                response = client.patch(
                    f"/users/{self.user_id}/status", json={"is_moderator": True}, headers=SUPER_ADMIN_HEADERS
                )
                if response.status_code != 200:
                    logger.error(f"Failed to set moderator rights: {response.text}")
                    self.environment.runner.quit()
                    return

                # Обновляем токен после изменения прав
                login_response = self.client.post(
                    "/auth/jwt/login",
                    data={"username": self.email, "password": "Test1234!"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if login_response.status_code == 200:
                    self.token = login_response.json()["access_token"]
                    self.headers["Authorization"] = f"Bearer {self.token}"
                    # Проверяем, что права действительно установлены
                    profile_response = self.client.get("/users/me", headers=self.headers)
                    if profile_response.status_code == 200:
                        user_data = profile_response.json()
                        if user_data.get("is_moderator"):
                            self.is_moderator = True
                            logger.info(f"Moderator rights successfully set for user {self.email}")
                        else:
                            logger.error("Moderator rights not set properly")
                            self.environment.runner.quit()
                    else:
                        logger.error(f"Failed to verify moderator rights: {profile_response.text}")
                        self.environment.runner.quit()
                else:
                    logger.error(f"Failed to update token after setting moderator rights: {login_response.text}")
                    self.environment.runner.quit()
            except Exception as e:
                logger.error(f"Error setting moderator rights: {str(e)}")
                self.environment.runner.quit()

    @task(3)  # Увеличено с 1
    @tag("moderator")
    def moderate_comments(self):
        """Модерация комментариев"""
        if not self.token or not self.is_moderator:
            return
        try:
            # Получаем список комментариев
            response = self.client.get("/comments/moderation", headers=self.headers)
            if response.status_code == 200:
                comments = response.json()
                if comments:
                    comment = random.choice(comments)
                    # Одобряем или отклоняем комментарий
                    action = random.choice(["approve", "reject"])
                    self.client.post(f"/comments/{comment['id']}/{action}", headers=self.headers)
        except Exception as e:
            logger.error(f"Error in moderate_comments: {str(e)}")

    @task(2)  # Увеличено с 1
    @tag("moderator")
    def create_book(self):
        """Создание новой книги (с проверкой)"""
        if not self.token or not self.is_moderator:
            return
        try:
            # Получаем необходимые данные
            authors = self.client.get("/authors/", headers=self.headers).json()
            categories = self.client.get("/categories/", headers=self.headers).json()
            tags = self.client.get("/tags/", headers=self.headers).json()

            if not all([authors, categories, tags]):
                return

            book_data = {
                "title": f"Test Book {uuid.uuid4().hex[:8]}",
                "description": f"Test description for load testing {uuid.uuid4().hex[:8]}",
                "language": random.choice(["ru", "en"]),
                "publication_year": random.randint(2000, 2024),
                "isbn": f"978-{random.randint(1000000000, 9999999999)}",
                "publisher": f"Test Publisher {uuid.uuid4().hex[:8]}",
                "file_url": f"test_{uuid.uuid4().hex[:8]}.pdf",
                "authors": [random.choice(authors)["id"]],
                "categories": [random.choice(categories)["id"]],
                "tags": [random.choice(tags)["id"]],
            }
            self.client.post("/books/", json=book_data, headers=self.headers)
        except Exception as e:
            logger.error(f"Error in create_book: {str(e)}")

    @task(2)
    @tag("moderator")
    def review_book(self):
        """Проверка книги"""
        if not self.token or not self.is_moderator:
            return
        try:
            # Получаем список книг на проверку
            response = self.client.get("/books/moderation", headers=self.headers)
            if response.status_code == 200:
                books = response.json()
                if books:
                    book = random.choice(books)
                    # Одобряем или отклоняем книгу
                    action = random.choice(["approve", "reject"])
                    review_data = {"comment": f"Test review {uuid.uuid4().hex[:8]}"}
                    self.client.post(f"/books/{book['id']}/{action}", json=review_data, headers=self.headers)
        except Exception as e:
            logger.error(f"Error in review_book: {str(e)}")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Инициализация при запуске Locust"""
    logger.info("Locust initialization started")
    logger.info(f"Test configuration: {USERS_COUNT} users, {SPAWN_RATE} users/sec")
    # Запускаем инициализацию супер-администратора в отдельном потоке
    spawn(init_super_admin)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Действия при начале теста"""
    logger.info("Test started")
    # Проверяем готовность супер-администратора
    if not SUPER_ADMIN_READY.is_set():
        logger.error("Super admin is not ready, stopping test")
        environment.runner.quit()
    # Устанавливаем количество пользователей и скорость их создания через environment.runner
    if hasattr(environment.runner, "user_classes_count"):
        environment.runner.user_classes_count = {
            "BooksPortalUser": int(USERS_COUNT * 0.5),  # 50% обычных пользователей
            "AdminUser": int(USERS_COUNT * 0.167),  # ~16.7% администраторов
            "ModeratorUser": int(USERS_COUNT * 0.333),  # ~33.3% модераторов
        }
    if hasattr(environment.runner, "spawn_rate"):
        environment.runner.spawn_rate = SPAWN_RATE


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Действия при остановке теста"""
    logger.info("Test stopped")
