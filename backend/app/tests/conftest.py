"""
Фикстуры для тестов
"""

import asyncio
import uuid
from typing import Generator

import httpx
import pytest
from fastapi_users.password import PasswordHelper
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.user import User

# Импортируем настройку путей
from .path_setup import *  # noqa: F403

# Базовый URL для тестов
BASE_URL = "http://test"

# Используем тестовую базу данных PostgreSQL
TEST_DATABASE_URL = settings.TEST_DATABASE_URL

# Данные тестового администратора
TEST_ADMIN_EMAIL = "book_owner_f51fea79@example.com"
TEST_ADMIN_PASSWORD = "Test1234!"

# Создаем экземпляр PasswordHelper для хеширования паролей
password_helper = PasswordHelper()

# Статистика тестов
test_stats = {
    "unit": {"total": 0, "passed": 0},
    "integration": {"total": 0, "passed": 0},
    "security": {"total": 0, "passed": 0},
}


def pytest_runtest_makereport(item, call):
    """Обновляет статистику тестов после каждого теста"""
    if call.when == "call":  # Только после выполнения теста
        test_type = "unit"  # По умолчанию
        if "integration" in item.nodeid:
            test_type = "integration"
        elif "security" in item.nodeid:
            test_type = "security"

        test_stats[test_type]["total"] += 1
        if call.excinfo is None:  # Если тест прошел успешно
            test_stats[test_type]["passed"] += 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Вывод статистики по типам тестов"""
    terminalreporter.write_sep("=", "ИТОГОВАЯ СТАТИСТИКА ТЕСТОВ")
    total_tests = 0
    total_passed = 0

    for test_type in test_stats:
        total = test_stats[test_type]["total"]
        passed = test_stats[test_type]["passed"]
        total_tests += total
        total_passed += passed

        if total > 0:
            percentage = (passed / total) * 100
            terminalreporter.write_sep("-", f"{test_type.upper()} тесты:")
            terminalreporter.write_line(f"  Всего тестов: {total}")
            terminalreporter.write_line(f"  Пройдено: {passed}")
            terminalreporter.write_line(f"  Процент успешных: {percentage:.1f}%")

    if total_tests > 0:
        overall_percentage = (total_passed / total_tests) * 100
        terminalreporter.write_sep("=", "ОБЩАЯ СТАТИСТИКА")
        terminalreporter.write_line(f"Всего тестов: {total_tests}")
        terminalreporter.write_line(f"Всего пройдено: {total_passed}")
        terminalreporter.write_line(f"Общий процент успешных: {overall_percentage:.1f}%")

    terminalreporter.write_sep("=", "КОНЕЦ ОТЧЕТА")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Создает новый event loop для тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Создает тестовый движок базы данных"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
async def async_session_maker(test_engine):
    """Фикстура для создания асинхронной сессии"""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    return async_session


@pytest.fixture
async def async_session(async_session_maker):
    """Фикстура для получения асинхронной сессии"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture
async def async_client(async_session_maker):
    """Фикстура для создания тестового клиента"""

    async def override_get_db():
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(async_session: AsyncSession):
    """Фикстура для создания тестового пользователя в базе данных с правами модератора"""
    user = User(
        email=f"test_db_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_moderator=True,  # Добавляем права модератора
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture(scope="session")
async def test_admin(async_session_maker):
    """Фикстура для получения тестового администратора"""
    async with async_session_maker() as session:
        # Получаем администратора из базы данных
        result = await session.execute(select(User).where(User.email == TEST_ADMIN_EMAIL))
        admin = result.scalar_one_or_none()

        if not admin:
            # Если администратор не существует, создаем его
            hashed_password = password_helper.hash(TEST_ADMIN_PASSWORD)
            admin = User(
                email=TEST_ADMIN_EMAIL,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True,
                is_verified=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
        else:
            # Если администратор существует, обновляем его пароль и права
            hashed_password = password_helper.hash(TEST_ADMIN_PASSWORD)
            await session.execute(
                update(User)
                .where(User.email == TEST_ADMIN_EMAIL)
                .values(hashed_password=hashed_password, is_active=True, is_superuser=True, is_verified=True)
            )
            await session.commit()
            await session.refresh(admin)

        # Проверяем права администратора
        if not admin.is_superuser:
            raise Exception(
                f"Пользователь {TEST_ADMIN_EMAIL} не имеет прав администратора! "
                f"Необходимо установить флаг is_superuser=True."
            )

        # Добавляем пароль для использования в тестах
        admin.plain_password = TEST_ADMIN_PASSWORD
        return admin


@pytest.fixture
async def auth_headers(async_client: AsyncClient, test_admin: User):
    """Фикстура для получения заголовков с токеном тестового администратора"""
    login_data = {"username": test_admin.email, "password": test_admin.plain_password}

    login_response = await async_client.post(
        "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == 200, f"Ошибка входа: {login_response.text}"
    token_data = login_response.json()

    return {"Authorization": f"Bearer {token_data['access_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="function")
async def test_user_with_token(async_client: httpx.AsyncClient) -> dict:
    """Создает тестового пользователя с правами модератора и возвращает его данные с токеном"""
    email = f"test_user_{asyncio.get_event_loop().time()}@example.com"
    password = "Test1234!"

    # Регистрация пользователя с правами модератора
    user_data = {
        "email": email,
        "password": password,
        "is_active": True,
        "is_moderator": True,  # Добавляем права модератора
    }

    response = await async_client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    # Получение токена
    login_data = {"username": email, "password": password}
    login_response = await async_client.post(
        "/auth/jwt/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == 200

    token_data = login_response.json()
    return {"email": email, "password": password, "token": token_data["access_token"]}


@pytest.fixture(scope="function")
async def auth_headers_with_token(test_user_with_token: dict) -> dict:
    """Возвращает заголовки с токеном авторизации"""
    return {"Authorization": f"Bearer {test_user_with_token['token']}", "Content-Type": "application/json"}
