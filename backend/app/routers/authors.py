from typing import List

from auth import admin_or_moderator, check_admin
from fastapi import APIRouter, Depends, status
from models.book import Author as AuthorModel
from models.user import User
from schemas.book import Author, AuthorCreate, AuthorUpdate
from services.book_servise import AuthorRepository
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    AuthorNotFoundException,
    DatabaseException,
    InvalidAuthorDataException,
    PermissionDeniedException,
)
from app.core.logger_config import (
    log_db_error,
    log_info,
    log_warning,
)

router = APIRouter(tags=["authors"])


@router.post(
    "/", response_model=Author, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_moderator)]
)
async def create_author(
    author_data: AuthorCreate, session: AsyncSession = Depends(get_db), current_user: User = Depends(check_admin)
):
    """Создание нового автора (доступно только для админов и модераторов)"""
    try:
        log_info(f"Creating new author: {author_data.name}")

        # Проверяем, существует ли автор с таким именем
        stmt = select(AuthorModel).where(AuthorModel.name == author_data.name)
        result = await session.execute(stmt)
        existing_author = result.scalars().first()

        if existing_author:
            log_warning(f"Attempt to create duplicate author: {author_data.name}")
            raise InvalidAuthorDataException(f"Автор с именем '{author_data.name}' уже существует")

        author_repo = AuthorRepository(session)
        author = await author_repo.create(author_data)
        log_info(f"Author created successfully: {author.name} (id: {author.id})")
        return author
    except (InvalidAuthorDataException, PermissionDeniedException):
        raise
    except IntegrityError as e:
        await session.rollback()
        log_db_error(e, operation="create_author", table="authors")
        raise InvalidAuthorDataException("Ошибка при создании автора")
    except Exception as e:
        await session.rollback()
        log_db_error(e, operation="create_author", table="authors")
        raise DatabaseException("Ошибка при создании автора")


@router.get("/", response_model=List[Author])
async def get_all_authors(session: AsyncSession = Depends(get_db)):
    """Получение списка всех авторов"""
    try:
        log_info("Getting all authors")
        author_repo = AuthorRepository(session)
        authors = await author_repo.get_all()
        log_info(f"Found {len(authors)} authors")
        return authors
    except Exception as e:
        log_db_error(e, operation="get_all_authors", table="authors")
        raise DatabaseException("Ошибка при получении списка авторов")


@router.get("/{author_id}", response_model=Author)
async def get_author(author_id: int, session: AsyncSession = Depends(get_db)):
    """Получение автора по ID"""
    try:
        log_info(f"Getting author with id: {author_id}")
        author_repo = AuthorRepository(session)
        author = await author_repo.get_by_id(author_id)
        if not author:
            log_warning(f"Author not found: id={author_id}")
            raise AuthorNotFoundException(message=f"Автор с ID {author_id} не найден")
        log_info(f"Found author: {author.name} (id: {author.id})")
        return author
    except AuthorNotFoundException:
        raise
    except Exception as e:
        log_db_error(e, operation="get_author", table="authors", author_id=author_id)
        raise DatabaseException("Ошибка при получении автора")


@router.put("/{author_id}", response_model=Author, dependencies=[Depends(admin_or_moderator)])
async def update_author(author_id: int, author_data: AuthorUpdate, session: AsyncSession = Depends(get_db)):
    """Обновление автора (доступно только для админов и модераторов)"""
    try:
        log_info(f"Updating author with id: {author_id}")
        author_repo = AuthorRepository(session)
        author = await author_repo.update(author_id, author_data)
        if not author:
            log_warning(f"Author not found for update: id={author_id}")
            raise AuthorNotFoundException(message=f"Автор с ID {author_id} не найден")
        log_info(f"Author updated successfully: {author.name} (id: {author.id})")
        return author
    except (AuthorNotFoundException, PermissionDeniedException):
        raise
    except IntegrityError as e:
        await session.rollback()
        log_db_error(e, operation="update_author", table="authors", author_id=author_id)
        raise InvalidAuthorDataException("Ошибка при обновлении автора")
    except Exception as e:
        await session.rollback()
        log_db_error(e, operation="update_author", table="authors", author_id=author_id)
        raise DatabaseException("Ошибка при обновлении автора")


@router.delete("/{author_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_moderator)])
async def delete_author(author_id: int, session: AsyncSession = Depends(get_db)):
    """Удаление автора (доступно только для админов и модераторов)"""
    try:
        log_info(f"Deleting author with id: {author_id}")
        author_repo = AuthorRepository(session)
        result = await author_repo.delete(author_id)
        if not result:
            log_warning(f"Author not found for deletion: id={author_id}")
            raise AuthorNotFoundException(message=f"Автор с ID {author_id} не найден")
        log_info(f"Author deleted successfully: id={author_id}")
        return None
    except (AuthorNotFoundException, PermissionDeniedException):
        raise
    except Exception as e:
        await session.rollback()
        log_db_error(e, operation="delete_author", table="authors", author_id=author_id)
        raise DatabaseException("Ошибка при удалении автора")
