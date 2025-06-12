import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis import Redis
from schemas.user import UserResponse
from services.users import UserService
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_redis_client
from app.core.logger_config import (
    log_cache_error,
    log_db_error,
    log_info,
)
from app.utils.json_serializer import deserialize_from_json, serialize_to_json

router = APIRouter(tags=["users"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> UserResponse:
    """
    Получение пользователя по ID.

    Args:
        user_id: ID пользователя
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        UserResponse: Информация о пользователе

    Raises:
        HTTPException: Если пользователь не найден или произошла ошибка
    """
    try:
        # Пытаемся получить из кэша
        if redis_client is not None:
            try:
                cache_key = f"user:{user_id}"
                cached_user = await redis_client.get(cache_key)
                if cached_user:
                    try:
                        user_data = deserialize_from_json(cached_user)
                        log_info(f"Successfully retrieved user {user_id} from cache")
                        return UserResponse(**user_data)
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_user",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_user",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем пользователя из БД
        user_service = UserService(db)
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Пользователь с ID {user_id} не найден")

        # Преобразуем в Pydantic модель
        user_response = UserResponse.model_validate(user)

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(user_response),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached user {user_id}")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_user",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return user_response
    except HTTPException:
        raise
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_user",
                "user_id": user_id,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении пользователя"
        )


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> List[UserResponse]:
    """
    Получение списка пользователей с пагинацией.

    Args:
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        db: Сессия базы данных
        redis_client: Клиент Redis

    Returns:
        List[UserResponse]: Список пользователей

    Raises:
        HTTPException: Если произошла ошибка при получении пользователей
    """
    try:
        # Пытаемся получить из кэша
        if redis_client is not None:
            try:
                cache_key = f"users:list:{skip}:{limit}"
                cached_users = await redis_client.get(cache_key)
                if cached_users:
                    try:
                        users_data = deserialize_from_json(cached_users)
                        log_info(f"Successfully retrieved {len(users_data)} users from cache")
                        return [UserResponse(**user) for user in users_data]
                    except json.JSONDecodeError as e:
                        log_cache_error(
                            e,
                            {
                                "operation": "parse_cached_users",
                                "key": cache_key,
                                "error_type": type(e).__name__,
                                "error_details": str(e),
                            },
                        )
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "get_users",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        # Получаем пользователей из БД
        user_service = UserService(db)
        users = await user_service.get_users(skip=skip, limit=limit)

        # Преобразуем в Pydantic модели
        user_responses = [UserResponse.model_validate(user) for user in users]

        # Сохраняем в кэш
        if redis_client is not None:
            try:
                await redis_client.set(
                    cache_key,
                    serialize_to_json(user_responses),
                    expire=3600,  # 1 час
                )
                log_info(f"Successfully cached {len(user_responses)} users")
            except Exception as e:
                log_cache_error(
                    e,
                    {
                        "operation": "cache_users",
                        "key": cache_key,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

        return user_responses
    except Exception as e:
        log_db_error(
            e,
            {
                "operation": "get_users",
                "skip": skip,
                "limit": limit,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении списка пользователей"
        )
