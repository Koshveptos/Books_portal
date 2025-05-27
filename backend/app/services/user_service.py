from uuid import UUID

from models.user import User
from sqlalchemy import exc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseException, UserNotFoundException
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
                raise UserNotFoundException(f"Пользователь с ID {user_id} не найден")
            return user
        except UserNotFoundException:
            raise
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error getting user by ID {user_id}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Ошибка при получении пользователя из базы данных")
        except Exception as e:
            logger.error(f"Unexpected error getting user by ID {user_id}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Непредвиденная ошибка при получении пользователя")

    async def get_by_email(self, email: str) -> User | None:
        """Получает пользователя по email"""
        try:
            query = select(User).where(User.email == email)
            result = await self.db.execute(query)
            user = result.scalars().first()

            if not user:
                logger.warning(f"User with email {email} not found")
                raise UserNotFoundException(f"Пользователь с email {email} не найден")
            return user
        except UserNotFoundException:
            raise
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error getting user by email {email}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Ошибка при получении пользователя из базы данных")
        except Exception as e:
            logger.error(f"Unexpected error getting user by email {email}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Непредвиденная ошибка при получении пользователя")

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получает пользователя по Telegram ID"""
        try:
            query = select(User).where(User.telegram_id == str(telegram_id))
            result = await self.db.execute(query)
            user = result.scalars().first()

            if not user:
                logger.warning(f"User with Telegram ID {telegram_id} not found")
                raise UserNotFoundException(f"Пользователь с Telegram ID {telegram_id} не найден")
            return user
        except UserNotFoundException:
            raise
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error getting user by Telegram ID {telegram_id}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Ошибка при получении пользователя из базы данных")
        except Exception as e:
            logger.error(f"Unexpected error getting user by Telegram ID {telegram_id}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Непредвиденная ошибка при получении пользователя")

    async def link_telegram(self, user_id: int, telegram_id: int) -> User:
        """Привязывает Telegram ID к пользователю"""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                raise UserNotFoundException(f"Пользователь с ID {user_id} не найден")

            # Проверяем, не привязан ли уже этот Telegram ID к другому пользователю
            existing_user = await self.get_by_telegram_id(telegram_id)
            if existing_user:
                raise ValueError(f"Telegram ID {telegram_id} уже привязан к другому пользователю")

            user.telegram_id = str(telegram_id)
            await self.update(user)
            logger.info(f"Successfully linked Telegram ID {telegram_id} to user {user.email}")
            return user
        except (UserNotFoundException, ValueError):
            raise
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error linking Telegram ID {telegram_id} to user {user_id}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Ошибка при привязке Telegram ID к пользователю")
        except Exception as e:
            logger.error(f"Unexpected error linking Telegram ID {telegram_id} to user {user_id}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Непредвиденная ошибка при привязке Telegram ID")

    async def unlink_telegram(self, user_id: int) -> User:
        """Отвязывает Telegram ID от пользователя"""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                raise UserNotFoundException(f"Пользователь с ID {user_id} не найден")

            if not user.telegram_id:
                raise ValueError(f"У пользователя {user_id} нет привязанного Telegram ID")

            user.telegram_id = None
            await self.update(user)
            logger.info(f"Successfully unlinked Telegram ID from user {user.email}")
            return user
        except (UserNotFoundException, ValueError):
            raise
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error unlinking Telegram ID from user {user_id}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Ошибка при отвязке Telegram ID от пользователя")
        except Exception as e:
            logger.error(f"Unexpected error unlinking Telegram ID from user {user_id}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Непредвиденная ошибка при отвязке Telegram ID")

    async def update(self, user: User) -> User:
        """Обновляет пользователя в базе данных"""
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"User {user.email} updated successfully")
            return user
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error updating user {user.email}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Ошибка при обновлении пользователя в базе данных")
        except Exception as e:
            logger.error(f"Unexpected error updating user {user.email}: {str(e)}")
            await self.db.rollback()
            raise DatabaseException("Непредвиденная ошибка при обновлении пользователя")
