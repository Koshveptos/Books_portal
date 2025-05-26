from uuid import UUID

from models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger_config import logger


class UserService:
    """Сервис для работы с пользователями"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Получает пользователя по ID"""
        try:
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalars().first()

            if not user:
                logger.warning(f"User with ID {user_id} not found")
            return user
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            await self.db.rollback()
            return None

    async def get_by_email(self, email: str) -> User | None:
        """Получает пользователя по email"""
        try:
            query = select(User).where(User.email == email)
            result = await self.db.execute(query)
            user = result.scalars().first()

            if not user:
                logger.warning(f"User with email {email} not found")
            return user
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            await self.db.rollback()
            return None

    async def update(self, user: User) -> User:
        """Обновляет пользователя в базе данных"""
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"User {user.email} updated successfully")
            return user
        except Exception as e:
            logger.error(f"Error updating user {user.email}: {str(e)}")
            await self.db.rollback()
            raise
