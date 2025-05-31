"""
Тесты для проверки защиты от SQL-инъекций
"""

import pytest
from httpx import AsyncClient

from app.tests.conftest import test_stats


@pytest.mark.asyncio
async def test_sql_injection_in_search(async_client: AsyncClient, auth_headers: dict):
    """Тест на SQL-инъекции в поисковом запросе"""
    test_stats["security"]["total"] += 1
    try:
        # Список потенциально опасных SQL-инъекций
        sql_injections = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' UNION SELECT * FROM users --",
            "'; DROP TABLE books; --",
            "' OR 1=1; --",
            "' OR 'x'='x",
            "admin' --",
            "admin' #",
            "' OR '1'='1' /*",
            "' OR 1=1/*",
            "') OR ('1'='1",
            "')) OR (('1'='1",
            "' OR '1'='1' LIMIT 1 --",
            "' OR '1'='1' ORDER BY 1 --",
            "' OR '1'='1' GROUP BY 1 --",
        ]

        for injection in sql_injections:
            # Тестируем поиск книг
            response = await async_client.get(f"/search/?q={injection}&limit=10", headers=auth_headers)
            assert response.status_code in [200, 400, 404], f"Неожиданный код ответа для инъекции {injection}"
            assert "error" not in response.text.lower(), f"Обнаружена уязвимость SQL-инъекции в поиске: {injection}"

            # Тестируем поиск по автору
            response = await async_client.get(f"/authors/search/?q={injection}", headers=auth_headers)
            assert response.status_code in [200, 400, 404], f"Неожиданный код ответа для инъекции {injection}"
            assert (
                "error" not in response.text.lower()
            ), f"Обнаружена уязвимость SQL-инъекции в поиске авторов: {injection}"

        test_stats["security"]["passed"] += 1
    except Exception as e:
        print(f"Тест не пройден: {str(e)}")
        raise


@pytest.mark.asyncio
async def test_sql_injection_in_filters(async_client: AsyncClient, auth_headers: dict):
    """Тест на SQL-инъекции в фильтрах"""
    test_stats["security"]["total"] += 1
    try:
        # Список потенциально опасных SQL-инъекций для фильтров
        sql_injections = [
            "1' OR '1'='1",
            "1' OR '1'='1' --",
            "1' UNION SELECT * FROM users --",
            "1; DROP TABLE books; --",
            "1' OR 1=1; --",
            "1' OR 'x'='x",
            "1' --",
            "1' #",
            "1' OR '1'='1' /*",
            "1' OR 1=1/*",
            "1) OR (1=1",
            "1)) OR ((1=1",
            "1' OR '1'='1' LIMIT 1 --",
            "1' OR '1'='1' ORDER BY 1 --",
            "1' OR '1'='1' GROUP BY 1 --",
        ]

        for injection in sql_injections:
            # Тестируем фильтрацию книг
            response = await async_client.get(f"/books/?year={injection}", headers=auth_headers)
            assert response.status_code in [200, 400, 404], f"Неожиданный код ответа для инъекции {injection}"
            assert "error" not in response.text.lower(), f"Обнаружена уязвимость SQL-инъекции в фильтрах: {injection}"

            # Тестируем фильтрацию по категориям
            response = await async_client.get(f"/books/?category={injection}", headers=auth_headers)
            assert response.status_code in [200, 400, 404], f"Неожиданный код ответа для инъекции {injection}"
            assert (
                "error" not in response.text.lower()
            ), f"Обнаружена уязвимость SQL-инъекции в фильтрах категорий: {injection}"

        test_stats["security"]["passed"] += 1
    except Exception as e:
        print(f"Тест не пройден: {str(e)}")
        raise


@pytest.mark.asyncio
async def test_sql_injection_in_authentication(async_client: AsyncClient):
    """Тест на SQL-инъекции в аутентификации"""
    test_stats["security"]["total"] += 1
    try:
        # Список потенциально опасных SQL-инъекций для аутентификации
        sql_injections = [
            "admin' --",
            "admin' #",
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR '1'='1' #",
            "' OR '1'='1'/*",
            "admin' OR '1'='1",
            "admin' OR '1'='1' --",
            "admin' OR '1'='1' #",
            "admin' OR '1'='1'/*",
            "' OR 1=1; --",
            "' OR 1=1; #",
            "' OR 1=1;/*",
            "admin' OR 1=1; --",
            "admin' OR 1=1; #",
            "admin' OR 1=1;/*",
        ]

        for injection in sql_injections:
            # Тестируем вход с SQL-инъекцией в email
            login_data = {"username": injection, "password": "any_password"}
            response = await async_client.post(
                "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            assert response.status_code in [400, 401], f"Неожиданный код ответа для инъекции {injection}"
            assert (
                "error" not in response.text.lower()
            ), f"Обнаружена уязвимость SQL-инъекции в аутентификации: {injection}"

            # Тестируем регистрацию с SQL-инъекцией
            register_data = {"email": injection, "password": "Test1234!", "is_active": True}
            response = await async_client.post("/auth/register", json=register_data)
            assert response.status_code in [400, 409], f"Неожиданный код ответа для инъекции {injection}"
            assert (
                "error" not in response.text.lower()
            ), f"Обнаружена уязвимость SQL-инъекции в регистрации: {injection}"

        test_stats["security"]["passed"] += 1
    except Exception as e:
        print(f"Тест не пройден: {str(e)}")
        raise


@pytest.mark.asyncio
async def test_sql_injection_in_book_operations(async_client: AsyncClient, auth_headers: dict):
    """Тест на SQL-инъекции в операциях с книгами"""
    test_stats["security"]["total"] += 1
    try:
        # Список потенциально опасных SQL-инъекций для операций с книгами
        sql_injections = [
            "1' OR '1'='1",
            "1' OR '1'='1' --",
            "1' UNION SELECT * FROM users --",
            "1; DROP TABLE books; --",
            "1' OR 1=1; --",
            "1' OR 'x'='x",
            "1' --",
            "1' #",
            "1' OR '1'='1' /*",
            "1' OR 1=1/*",
            "1) OR (1=1",
            "1)) OR ((1=1",
        ]

        for injection in sql_injections:
            # Тестируем получение книги по ID
            response = await async_client.get(f"/books/{injection}", headers=auth_headers)
            assert response.status_code in [400, 404], f"Неожиданный код ответа для инъекции {injection}"
            assert (
                "error" not in response.text.lower()
            ), f"Обнаружена уязвимость SQL-инъекции в получении книги: {injection}"

            # Тестируем обновление книги
            update_data = {"title": injection, "description": "Test description"}
            response = await async_client.patch("/books/1", headers=auth_headers, json=update_data)
            assert response.status_code in [200, 400, 404], f"Неожиданный код ответа для инъекции {injection}"
            assert (
                "error" not in response.text.lower()
            ), f"Обнаружена уязвимость SQL-инъекции в обновлении книги: {injection}"

        test_stats["security"]["passed"] += 1
    except Exception as e:
        print(f"Тест не пройден: {str(e)}")
        raise
