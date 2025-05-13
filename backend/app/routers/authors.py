import traceback
from typing import List

from auth import admin_or_moderator, check_admin
from core.database import get_db
from core.exceptions import AuthorNotFoundException, InvalidAuthorDataException
from core.logger_config import logger
from fastapi import APIRouter, Depends, HTTPException, status
from models.book import Author as AuthorModel
from models.user import User
from schemas.book import Author, AuthorCreate, AuthorUpdate
from services.book_servise import AuthorRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["authors"])


@router.post(
    "/", response_model=Author, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_moderator)]
)
async def create_author(
    author_data: AuthorCreate, session: AsyncSession = Depends(get_db), current_user: User = Depends(check_admin)
):
    """Создание нового автора (доступно только для админов и модераторов)"""
    logger.info(f"Creating new author: {author_data.name}")
    try:
        # Проверяем, существует ли автор с таким именем
        stmt = select(AuthorModel).where(AuthorModel.name == author_data.name)
        result = await session.execute(stmt)
        existing_author = result.scalars().first()

        if existing_author:
            logger.warning(f"Attempt to create duplicate author: {author_data.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"Автор с именем '{author_data.name}' уже существует"
            )

        logger.debug(f"Creating AuthorRepository instance with session: {session}")
        author_repo = AuthorRepository(session)
        logger.debug(f"Calling author_repo.create with data: {author_data.dict()}")
        author = await author_repo.create(author_data)
        logger.info(f"Author created successfully: {author.name} (id: {author.id})")
        return author
    except NotImplementedError as nie:
        error_msg = "Метод создания автора не реализован"
        logger.error(f"Error creating author - NotImplementedError: {str(nie)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=error_msg)
    except Exception as e:
        logger.error(f"Error creating author: {str(e)}\n{traceback.format_exc()}")
        raise InvalidAuthorDataException(message=f"Ошибка при создании автора: {str(e)}")


@router.get("/", response_model=List[Author])
async def get_all_authors(session: AsyncSession = Depends(get_db)):
    """Получение списка всех авторов"""
    logger.info("Getting all authors")
    author_repo = AuthorRepository(session)
    authors = await author_repo.get_all()
    logger.info(f"Found {len(authors)} authors")
    return authors


@router.get("/{author_id}", response_model=Author)
async def get_author(author_id: int, session: AsyncSession = Depends(get_db)):
    """Получение автора по ID"""
    logger.info(f"Getting author with id: {author_id}")
    author_repo = AuthorRepository(session)
    author = await author_repo.get_by_id(author_id)
    if not author:
        logger.warning(f"Author not found: id={author_id}")
        raise AuthorNotFoundException(message=f"Автор с ID {author_id} не найден")
    logger.info(f"Found author: {author.name} (id: {author.id})")
    return author


@router.put("/{author_id}", response_model=Author, dependencies=[Depends(admin_or_moderator)])
async def update_author(author_id: int, author_data: AuthorUpdate, session: AsyncSession = Depends(get_db)):
    """Обновление автора (доступно только для админов и модераторов)"""
    logger.info(f"Updating author with id: {author_id}")
    author_repo = AuthorRepository(session)
    author = await author_repo.update(author_id, author_data)
    if not author:
        logger.warning(f"Author not found for update: id={author_id}")
        raise AuthorNotFoundException(message=f"Автор с ID {author_id} не найден")
    logger.info(f"Author updated successfully: {author.name} (id: {author.id})")
    return author


@router.delete("/{author_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_moderator)])
async def delete_author(author_id: int, session: AsyncSession = Depends(get_db)):
    """Удаление автора (доступно только для админов и модераторов)"""
    logger.info(f"Deleting author with id: {author_id}")
    author_repo = AuthorRepository(session)
    result = await author_repo.delete(author_id)
    if not result:
        logger.warning(f"Author not found for deletion: id={author_id}")
        raise AuthorNotFoundException(message=f"Автор с ID {author_id} не найден")
    logger.info(f"Author deleted successfully: id={author_id}")
    return None
