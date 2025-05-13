"""
Маршруты API для пользователей
"""

from core.auth import current_active_user, current_moderator
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Path, status
from models.user import User
from schemas.user import UserResponse, UserUpdate
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(current_active_user)):
    """
    Получить информацию о текущем пользователе.

    Требуется Bearer JWT токен авторизации.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необходима авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


@router.get("/check-moderator")
async def check_moderator_status(current_user: User = Depends(current_active_user)):
    """
    Проверить, является ли текущий пользователь модератором.

    Требуется Bearer JWT токен авторизации.

    Возвращает:
        {"is_moderator": true} если пользователь является модератором
        {"is_moderator": false} если пользователь не является модератором
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необходима авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"is_moderator": current_user.is_moderator}


@router.post("/promote/{user_id}", response_model=UserResponse)
async def promote_to_moderator(
    user_id: int = Path(..., gt=0, description="ID пользователя для повышения"),
    current_user: User = Depends(current_moderator),
    db: AsyncSession = Depends(get_db),
):
    """
    Повысить пользователя до модератора (требуются права модератора).

    Args:
        user_id: ID пользователя для повышения
    """
    # Проверяем, существует ли пользователь
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    # Повышаем пользователя до модератора
    user.is_moderator = True
    await db.commit()
    await db.refresh(user)

    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить данные текущего пользователя
    """
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, key, value)

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return current_user
