from uuid import UUID

from core.logger_config import logger
from models.user import User
from sqlalchemy.orm import Session


class UserRepository:
    """Репозиторий для работы с пользователями"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        """Получает пользователя по ID"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User with ID {user_id} not found")
            return user
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            self.db.rollback()
            return None

    def get_by_email(self, email: str) -> User | None:
        """Получает пользователя по email"""
        try:
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                logger.warning(f"User with email {email} not found")
            return user
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            self.db.rollback()
            return None

    def update(self, user: User) -> User:
        """Обновляет пользователя в базе данных"""
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"User {user.email} updated successfully")
            return user
        except Exception as e:
            logger.error(f"Error updating user {user.email}: {str(e)}")
            self.db.rollback()
            raise
