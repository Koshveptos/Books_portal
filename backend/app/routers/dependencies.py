from auth import current_active_user
from core.logger_config import logger
from fastapi import Depends, HTTPException, status
from models.user import User


async def check_moderator_or_admin_permission(user: User = Depends(current_active_user)):
    """
    Проверяет, имеет ли пользователь права модератора или администратора.

    Аргументы:
        user: Текущий авторизованный пользователь

    Возвращает:
        True, если проверка пройдена успешно

    Вызывает:
        HTTPException: Если пользователь не имеет прав модератора или администратора
    """
    logger.debug(f"Checking moderator or admin permission for user {user.email} (id: {user.id})")

    if not user.is_moderator and not user.is_superuser:
        logger.warning(
            f"Permission denied: User {user.email} (id: {user.id}) " f"attempted to access moderator/admin resource"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Для доступа требуются права модератора или администратора"
        )

    logger.debug(f"Moderator or admin permission granted for user {user.email} (id: {user.id})")
    return True
