import random
import time

from locust import HttpUser, between, task
from locust.exception import RescheduleTask


class BooksPortalUser(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 3)
    max_retries = 3
    retry_delay = 1

    def on_start(self):
        for attempt in range(self.max_retries):
            try:
                # Регистрация пользователя
                register_data = {
                    "email": f"loadtest{random.randint(1, 1000000)}@example.com",
                    "username": f"loadtest{random.randint(1, 1000000)}",
                    "password": "testpassword123",
                }

                register_response = self.client.post("/auth/register", json=register_data)

                if register_response.status_code != 201:
                    print(f"Registration failed (attempt {attempt + 1}): {register_response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return

                # Вход пользователя
                login_data = {"username": register_data["email"], "password": register_data["password"]}

                login_response = self.client.post(
                    "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if login_response.status_code != 200:
                    print(f"Login failed (attempt {attempt + 1}): {login_response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return

                response_data = login_response.json()
                if "access_token" not in response_data:
                    print(f"Token not found in response (attempt {attempt + 1}): {response_data}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return

                self.token = response_data["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
                return

            except Exception as e:
                print(f"Error in on_start (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return

    def safe_request(self, method, url, **kwargs):
        try:
            response = getattr(self.client, method.lower())(url, **kwargs)
            if response.status_code in [200, 201, 204]:
                return response
            return None
        except Exception:
            return None

    @task(3)
    def get_books(self):
        try:
            response = self.safe_request("get", "/books/")
            if response is None:
                raise RescheduleTask()
        except Exception as e:
            print(f"Error in get_books: {str(e)}")
            raise RescheduleTask()

    @task(2)
    def get_categories(self):
        try:
            response = self.safe_request("get", "/categories/")
            if response is None:
                raise RescheduleTask()
        except Exception as e:
            print(f"Error in get_categories: {str(e)}")
            raise RescheduleTask()

    @task(2)
    def get_authors(self):
        try:
            response = self.safe_request("get", "/authors/")
            if response is None:
                raise RescheduleTask()
        except Exception as e:
            print(f"Error in get_authors: {str(e)}")
            raise RescheduleTask()

    @task(1)
    def get_book_details(self):
        try:
            # Сначала получаем список книг
            books_response = self.safe_request("get", "/books/")
            if books_response is None or books_response.status_code != 200:
                raise RescheduleTask()

            books = books_response.json()
            if not books:
                raise RescheduleTask()

            # Выбираем случайную книгу и получаем её детали
            book = random.choice(books)
            book_details = self.safe_request("get", f"/books/{book['id']}")
            if book_details is None:
                raise RescheduleTask()

        except Exception as e:
            print(f"Error in get_book_details: {str(e)}")
            raise RescheduleTask()

    @task(1)
    def get_category_books(self):
        try:
            # Сначала получаем список категорий
            categories_response = self.safe_request("get", "/categories/")
            if categories_response is None or categories_response.status_code != 200:
                raise RescheduleTask()

            categories = categories_response.json()
            if not categories:
                raise RescheduleTask()

            # Выбираем случайную категорию и получаем её книги
            category = random.choice(categories)
            books = self.safe_request("get", f"/categories/{category['id']}/books")
            if books is None:
                raise RescheduleTask()

        except Exception as e:
            print(f"Error in get_category_books: {str(e)}")
            raise RescheduleTask()

    @task(1)
    def get_author_books(self):
        try:
            # Сначала получаем список авторов
            authors_response = self.safe_request("get", "/authors/")
            if authors_response is None or authors_response.status_code != 200:
                raise RescheduleTask()

            authors = authors_response.json()
            if not authors:
                raise RescheduleTask()

            # Выбираем случайного автора и получаем его книги
            author = random.choice(authors)
            books = self.safe_request("get", f"/authors/{author['id']}/books")
            if books is None:
                raise RescheduleTask()

        except Exception as e:
            print(f"Error in get_author_books: {str(e)}")
            raise RescheduleTask()
