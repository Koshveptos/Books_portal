import random

from locust import HttpUser, between, task


class BooksPortalUser(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 3)

    def on_start(self):
        try:
            # Регистрация пользователя
            register_data = {
                "email": f"loadtest{random.randint(1, 1000000)}@example.com",
                "username": f"loadtest{random.randint(1, 1000000)}",
                "password": "testpassword123",
            }

            register_response = self.client.post("/auth/register", json=register_data)

            if register_response.status_code != 201:
                print(f"Registration failed: {register_response.text}")
                return

            # Вход пользователя
            login_data = {"username": register_data["email"], "password": register_data["password"]}

            login_response = self.client.post(
                "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if login_response.status_code != 200:
                print(f"Login failed: {login_response.text}")
                return

            response_data = login_response.json()
            if "access_token" not in response_data:
                print(f"Token not found in response: {response_data}")
                return

            self.token = response_data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

        except Exception as e:
            print(f"Error in on_start: {str(e)}")

    @task(3)
    def get_books(self):
        self.client.get("/books/")

    @task(2)
    def search_books(self):
        search_terms = ["python", "java", "javascript", "database", "web"]
        self.client.get(f"/books/search?query={random.choice(search_terms)}")

    @task(1)
    def create_book(self):
        if not hasattr(self, "headers"):
            return

        self.client.post(
            "/books/",
            headers=self.headers,
            json={
                "title": f"Load Test Book {random.randint(1, 1000000)}",
                "author": f"Load Test Author {random.randint(1, 1000000)}",
                "description": "Load test book description",
                "isbn": f"{random.randint(1000000000000, 9999999999999)}",
                "language": "ru",
            },
        )

    @task(1)
    def create_review(self):
        if not hasattr(self, "headers"):
            return

        # Сначала получаем список книг
        books_response = self.client.get("/books/")
        if books_response.status_code == 200:
            books = books_response.json()
            if books:
                book = random.choice(books)
                self.client.post(
                    f"/books/{book['id']}/ratings",
                    headers=self.headers,
                    json={"rating": random.randint(1, 5), "comment": "Load test review"},
                )
