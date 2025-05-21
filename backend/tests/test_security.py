import pytest
from fastapi import status

from tests.utils import create_test_token


@pytest.mark.asyncio
async def test_sql_injection_prevention(client, db):
    # Пытаемся выполнить SQL-инъекцию через параметры запроса
    malicious_input = "'; DROP TABLE users; --"

    response = client.get(f"/books/search?query={malicious_input}")
    assert response.status_code == status.HTTP_200_OK

    # Проверяем, что таблица users все еще существует
    result = await db.execute("SELECT 1 FROM users")
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_cors_headers(client):
    # Проверяем CORS-заголовки
    response = client.options("/books/")
    assert response.status_code == status.HTTP_200_OK
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers


@pytest.mark.asyncio
async def test_rate_limiting(client):
    # Проверяем ограничение количества запросов
    for _ in range(100):  # Делаем много запросов подряд
        response = client.get("/books/")
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            break
    else:
        pytest.fail("Rate limiting not working")


@pytest.mark.asyncio
async def test_password_hashing(client):
    # Регистрируем пользователя
    password = "testpassword123"
    response = client.post("/auth/register", json={"email": "security@example.com", "password": password})
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Проверяем, что пароль не возвращается в ответе
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_jwt_token_security(client, test_user):
    # Получаем токен
    response = client.post("/auth/jwt/login", data={"username": test_user.email, "password": "testpassword123"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data

    # Проверяем, что токен работает
    token = data["access_token"]
    response = client.get("/books/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK

    # Проверяем, что неверный токен отклоняется
    response = client.get("/books/", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_xss_prevention(client, test_user):
    # Пытаемся внедрить XSS через параметры запроса
    xss_payload = "<script>alert('xss')</script>"

    # Тестируем поиск
    response = client.get(f"/books/search?query={xss_payload}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert xss_payload not in str(data)

    # Тестируем создание книги
    access_token = create_test_token({"sub": test_user.email})
    response = client.post(
        "/books/",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "title": xss_payload,
            "isbn": "1234567890123",
            "description": xss_payload,
            "language": "ru",
            "file_url": "test.pdf",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert xss_payload not in str(data)
