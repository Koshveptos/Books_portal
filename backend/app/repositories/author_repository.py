from core.exceptions import InvalidAuthorDataException
from loguru import logger
from models.book import Author
from schemas.book import AuthorCreate, AuthorUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AuthorRepository:
    """
    Репозиторий для работы с авторами книг.

    Предоставляет методы для выполнения операций CRUD с сущностями авторов.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Инициализирует репозиторий авторов с указанной сессией базы данных.

        Args:
            db_session: Асинхронная сессия базы данных SQLAlchemy
        """
        self.db = db_session
        logger.debug("Создан репозиторий авторов")

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Author]:
        """
        Получает список всех авторов с пагинацией.

        Args:
            skip: Количество записей для пропуска
            limit: Максимальное количество записей для возврата

        Returns:
            Список авторов
        """
        logger.debug(f"Получение списка авторов (skip={skip}, limit={limit})")
        query = select(Author).offset(skip).limit(limit)
        result = await self.db.execute(query)
        authors = result.scalars().all()
        logger.debug(f"Найдено {len(authors)} авторов")
        return list(authors)

    async def get_by_id(self, author_id: int) -> Author | None:
        """
        Получает автора по его идентификатору.

        Args:
            author_id: Идентификатор автора

        Returns:
            Объект автора или None, если автор не найден
        """
        logger.debug(f"Поиск автора с ID={author_id}")
        query = select(Author).where(Author.id == author_id)
        result = await self.db.execute(query)
        author = result.scalars().first()
        if author:
            logger.debug(f"Найден автор с ID={author_id}: {author.name}")
        else:
            logger.debug(f"Автор с ID={author_id} не найден")
        return author

    async def get_by_name(self, name: str) -> Author | None:
        """
        Получает автора по его имени.

        Args:
            name: Имя автора

        Returns:
            Объект автора или None, если автор не найден
        """
        logger.debug(f"Поиск автора по имени: '{name}'")
        query = select(Author).where(Author.name == name)
        result = await self.db.execute(query)
        author = result.scalars().first()
        if author:
            logger.debug(f"Найден автор с именем '{name}': ID={author.id}")
        else:
            logger.debug(f"Автор с именем '{name}' не найден")
        return author

    async def create(self, author_data: AuthorCreate) -> Author:
        """
        Создает нового автора.

        Args:
            author_data: Данные для создания автора

        Returns:
            Созданный объект автора

        Raises:
            InvalidAuthorDataException: Если данные автора некорректны
        """
        logger.debug(f"Создание нового автора: {author_data.model_dump()}")
        try:
            # Валидация данных
            if not author_data.name or len(author_data.name.strip()) < 2:
                logger.error(f"Некорректное имя автора: '{author_data.name}'")
                raise InvalidAuthorDataException("Имя автора должно содержать не менее 2 символов")

            # Создание объекта автора
            db_author = Author(name=author_data.name)
            self.db.add(db_author)
            await self.db.commit()
            await self.db.refresh(db_author)
            logger.info(f"Создан новый автор: ID={db_author.id}, имя='{db_author.name}'")
            return db_author
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при создании автора: {str(e)}")
            raise

    async def update(self, author_id: int, author_data: AuthorUpdate) -> Author:
        """
        Обновляет информацию об авторе.

        Args:
            author_id: Идентификатор автора
            author_data: Данные для обновления

        Returns:
            Обновленный объект автора

        Raises:
            Exception: Если автор не найден или при обновлении произошла ошибка
        """
        logger.debug(f"Обновление автора с ID={author_id}: {author_data.model_dump()}")
        try:
            # Получение автора
            author = await self.get_by_id(author_id)
            if not author:
                logger.error(f"Автор с ID={author_id} не найден")
                raise Exception(f"Автор с ID={author_id} не найден")

            # Валидация данных
            if not author_data.name or len(author_data.name.strip()) < 2:
                logger.error(f"Некорректное имя автора: '{author_data.name}'")
                raise InvalidAuthorDataException("Имя автора должно содержать не менее 2 символов")

            # Обновление данных
            old_name = author.name
            author.name = author_data.name
            await self.db.commit()
            await self.db.refresh(author)
            logger.info(f"Обновлен автор с ID={author_id}: имя изменено с '{old_name}' на '{author.name}'")
            return author
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при обновлении автора с ID={author_id}: {str(e)}")
            raise

    async def delete(self, author_id: int) -> bool:
        """
        Удаляет автора по его идентификатору.

        Args:
            author_id: Идентификатор автора

        Returns:
            True, если автор успешно удален, иначе False

        Raises:
            Exception: Если автор не найден или при удалении произошла ошибка
        """
        logger.debug(f"Удаление автора с ID={author_id}")
        try:
            # Получение автора
            author = await self.get_by_id(author_id)
            if not author:
                logger.error(f"Автор с ID={author_id} не найден")
                raise Exception(f"Автор с ID={author_id} не найден")

            # Удаление автора
            await self.db.delete(author)
            await self.db.commit()
            logger.info(f"Удален автор с ID={author_id}, имя='{author.name}'")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при удалении автора с ID={author_id}: {str(e)}")
            raise
