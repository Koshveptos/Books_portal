from typing import List, Optional

from auth import current_active_user
from core.database import get_db
from core.logger_config import logger
from fastapi import APIRouter, Depends, HTTPException, Query
from models.book import Book
from models.user import User
from schemas.book import BookResponse
from services.books import BooksService
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(tags=["search"])


@router.get("/", response_model=List[BookResponse])
async def search_books(
    q: str = Query(..., min_length=3, description="Поисковый запрос (минимум 3 символа)"),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество результатов"),
    field: Optional[str] = Query(
        None, description="Поле для поиска (title, description или пусто для поиска по всем полям)"
    ),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Полнотекстовый поиск книг по названию и описанию.

    Запрос должен содержать минимум 3 символа.
    Результаты сортируются по релевантности.

    Поддерживаются операторы логики:
    - & (AND): слово1 & слово2
    - | (OR): слово1 | слово2
    - ! (NOT): !слово

    Для поиска фраз используйте кавычки: "точная фраза"

    Для поиска с учетом морфологии используйте суффикс :*
    Например: книг:* найдет "книга", "книги", "книгой" и т.д.

    Если операторы не указаны, по умолчанию используется AND с учетом морфологии.
    """
    try:
        logger.info(f"Пользователь {user.email} выполняет поиск: '{q}'{f' в поле {field}' if field else ''}")

        books_service = BooksService(db)
        books = await books_service.search_books(q, limit, field)

        if not books:
            logger.info(f"По запросу '{q}' книги не найдены")
            return []

        logger.info(f"По запросу '{q}' найдено {len(books)} книг")

        book_responses = []
        for book in books:
            if not (hasattr(book, "_sa_instance_state") and not book._sa_instance_state.unloaded):
                book_id = book.id
                query = (
                    select(Book)
                    .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
                    .where(Book.id == book_id)
                )
                result = await db.execute(query)
                book = result.scalar_one()

            book_responses.append(BookResponse.model_validate(book))

        return book_responses

    except Exception as e:
        logger.error(f"Ошибка при поиске книг: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при выполнении поиска")


@router.get("/by-author", response_model=List[BookResponse])
async def search_books_by_author(
    name: str = Query(..., min_length=3, description="Имя автора (минимум 3 символа)"),
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Поиск книг по имени автора.

    Поиск выполняется по частичному совпадению имени автора.
    """
    try:
        logger.info(f"Пользователь {user.email} ищет книги по автору: '{name}'")

        books_service = BooksService(db)
        books = await books_service.search_books_by_author(name, limit)

        if not books:
            logger.info(f"Книги по автору '{name}' не найдены")
            return []

        logger.info(f"Найдено {len(books)} книг по автору '{name}'")

        book_responses = []
        for book in books:
            if not (hasattr(book, "_sa_instance_state") and not book._sa_instance_state.unloaded):
                book_id = book.id
                query = (
                    select(Book)
                    .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
                    .where(Book.id == book_id)
                )
                result = await db.execute(query)
                book = result.scalar_one()

            book_responses.append(BookResponse.model_validate(book))

        return book_responses

    except Exception as e:
        logger.error(f"Ошибка при поиске книг по автору: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при выполнении поиска по автору")


@router.get("/suggest", response_model=List[str])
async def suggest_corrections(
    q: str = Query(..., min_length=3, description="Поисковый запрос для подсказок (минимум 3 символа)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Предлагает исправления для поискового запроса на основе сходства слов.

    Использует триграммное сравнение для нахождения похожих слов.
    """
    try:
        logger.info(f"Пользователь {user.email} запрашивает подсказки для запроса: '{q}'")

        if not q or len(q.strip()) < 3:
            logger.info("Запрос слишком короткий для подсказок")
            return []

        sql = """
            SELECT word, similarity
            FROM (
                SELECT title as word, similarity(title, :query) as similarity
                FROM books
                WHERE title % :query
                UNION
                SELECT name as word, similarity(name, :query) as similarity
                FROM authors
                WHERE name % :query
                UNION
                SELECT name_categories as word, similarity(name_categories, :query) as similarity
                FROM categories
                WHERE name_categories % :query
                UNION
                SELECT name_tag as word, similarity(name_tag, :query) as similarity
                FROM tags
                WHERE name_tag % :query
            ) as words
            WHERE similarity > 0.3
            ORDER BY similarity DESC
            LIMIT 5
        """

        result = await db.execute(text(sql), {"query": q.strip()})
        suggestions = [row.word for row in result.fetchall()]

        logger.info(f"Для запроса '{q}' найдено {len(suggestions)} подсказок")
        return suggestions

    except Exception as e:
        logger.error(f"Ошибка при формировании подсказок: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при формировании подсказок для поиска")


@router.post("/update-vectors")
async def update_search_vectors(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Обновить поисковые векторы для всех книг и авторов.

    Требуются права администратора.
    """
    if not user.is_superuser:
        logger.warning(f"Пользователь {user.email} пытается обновить поисковые векторы без прав администратора")
        raise HTTPException(status_code=403, detail="Требуются права администратора")

    try:
        logger.info(f"Пользователь {user.email} обновляет поисковые векторы")

        books_service = BooksService(db)
        count = await books_service.update_search_vectors()

        logger.info(f"Поисковые векторы обновлены для {count} книг")
        return {"message": f"Поисковые векторы обновлены для {count} книг"}

    except Exception as e:
        logger.error(f"Ошибка при обновлении поисковых векторов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при обновлении поисковых векторов")


@router.get("/field/{field_name}", response_model=List[BookResponse])
async def search_by_field(
    field_name: str,
    q: str = Query(..., min_length=3, description="Поисковый запрос (минимум 3 символа)"),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество результатов"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Поиск книг по конкретному полю.

    Доступные поля для поиска:
    - title: название книги
    - description: описание книги
    - publisher: издатель
    - isbn: ISBN книги

    Поиск учитывает морфологию русского языка.
    """
    valid_fields = ["title", "description", "publisher", "isbn"]
    if field_name not in valid_fields:
        logger.warning(f"Пользователь {user.email} пытается искать по неверному полю: {field_name}")
        raise HTTPException(
            status_code=400, detail=f"Неверное поле для поиска. Допустимые поля: {', '.join(valid_fields)}"
        )

    try:
        logger.info(f"Пользователь {user.email} выполняет поиск по полю {field_name}: '{q}'")

        books_service = BooksService(db)
        books = await books_service.search_by_field(field_name, q, limit)

        if not books:
            logger.info(f"По запросу '{q}' в поле {field_name} книги не найдены")
            return []

        logger.info(f"По запросу '{q}' в поле {field_name} найдено {len(books)} книг")

        book_responses = []
        for book in books:
            if not (hasattr(book, "_sa_instance_state") and not book._sa_instance_state.unloaded):
                book_id = book.id
                query = (
                    select(Book)
                    .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
                    .where(Book.id == book_id)
                )
                result = await db.execute(query)
                book = result.scalar_one()

            book_responses.append(BookResponse.model_validate(book))

        return book_responses

    except Exception as e:
        logger.error(f"Ошибка при поиске книг по полю {field_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при выполнении поиска по полю {field_name}")


@router.get("/advanced", response_model=List[BookResponse])
async def advanced_search(
    q: str = Query(..., min_length=3, description="Поисковый запрос (минимум 3 символа)"),
    title: Optional[str] = Query(None, description="Поиск по названию"),
    author: Optional[str] = Query(None, description="Поиск по автору"),
    category: Optional[str] = Query(None, description="Поиск по категории"),
    tag: Optional[str] = Query(None, description="Поиск по тегу"),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество результатов"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    Расширенный поиск книг с комбинацией различных критериев.

    Можно указать один или несколько параметров для поиска.
    Результаты будут соответствовать всем указанным критериям (логическое И).

    Поиск учитывает морфологию русского языка.
    """
    try:
        logger.info(
            f"Пользователь {user.email} выполняет расширенный поиск с параметрами: q='{q}', title='{title}', author='{author}', category='{category}', tag='{tag}'"
        )

        # Начинаем с общего поиска
        books_service = BooksService(db)
        books = await books_service.search_books(q, limit=100)  # Увеличиваем лимит для последующей фильтрации

        if not books:
            logger.info(f"По общему запросу '{q}' книги не найдены")
            return []

        # Фильтруем результаты по дополнительным критериям
        filtered_books = books

        # Фильтр по названию
        if title:
            title_lower = title.lower()
            filtered_books = [book for book in filtered_books if title_lower in book.title.lower()]
            logger.debug(f"После фильтрации по названию '{title}' осталось {len(filtered_books)} книг")

        # Фильтр по автору
        if author and filtered_books:
            author_lower = author.lower()
            filtered_books = [
                book for book in filtered_books if any(author_lower in a.name.lower() for a in book.authors)
            ]
            logger.debug(f"После фильтрации по автору '{author}' осталось {len(filtered_books)} книг")

        # Фильтр по категории
        if category and filtered_books:
            category_lower = category.lower()
            filtered_books = [
                book
                for book in filtered_books
                if any(category_lower in c.name_categories.lower() for c in book.categories)
            ]
            logger.debug(f"После фильтрации по категории '{category}' осталось {len(filtered_books)} книг")

        # Фильтр по тегу
        if tag and filtered_books:
            tag_lower = tag.lower()
            filtered_books = [
                book for book in filtered_books if any(tag_lower in t.name_tag.lower() for t in book.tags)
            ]
            logger.debug(f"После фильтрации по тегу '{tag}' осталось {len(filtered_books)} книг")

        # Ограничиваем количество результатов
        result_books = filtered_books[:limit]

        if not result_books:
            logger.info("После применения всех фильтров книги не найдены")
            return []

        logger.info(f"По расширенному запросу найдено {len(result_books)} книг")

        # Преобразуем в Pydantic-модели
        book_responses = []
        for book in result_books:
            if not (hasattr(book, "_sa_instance_state") and not book._sa_instance_state.unloaded):
                book_id = book.id
                query = (
                    select(Book)
                    .options(selectinload(Book.authors), selectinload(Book.categories), selectinload(Book.tags))
                    .where(Book.id == book_id)
                )
                result = await db.execute(query)
                book = result.scalar_one()

            book_responses.append(BookResponse.model_validate(book))

        return book_responses

    except Exception as e:
        logger.error(f"Ошибка при выполнении расширенного поиска: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при выполнении расширенного поиска")
