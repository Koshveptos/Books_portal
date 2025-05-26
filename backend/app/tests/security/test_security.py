"""
Тесты безопасности
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_jwt_token_expiration(async_client: AsyncClient, test_user_with_token: dict):
    """Тест на истечение срока действия JWT токена"""
    # Получаем токен
    token = test_user_with_token["token"]

    # Проверяем, что токен действителен
    response = await async_client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    # TODO: Добавить тест на проверку истечения срока действия токена
    # Для этого нужно либо ждать истечения срока действия токена,
    # либо модифицировать время жизни токена в тестовой среде


@pytest.mark.asyncio
async def test_invalid_token_format(async_client: AsyncClient):
    """Тест на обработку неверного формата токена"""
    # Тест с неверным форматом токена
    response = await async_client.get("/users/me", headers={"Authorization": "Bearer invalid_token_format"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_access_control(async_client: AsyncClient, test_user_with_token: dict):
    """Тест на контроль доступа к защищенным ресурсам"""
    # Тест без токена
    response = await async_client.get("/users/me")
    assert response.status_code == 401

    # Тест с токеном
    token = test_user_with_token["token"]
    response = await async_client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
