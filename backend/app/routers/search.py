from typing import List, Optional

from auth import current_active_user
from fastapi import APIRouter, Depends, Query
from models.book import Book
from models.user import User
from schemas.book import BookResponse
from services.books import BooksService
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import (
    DatabaseException,
    InvalidSearchQueryException,
    PermissionDeniedException,
    SearchException,
)
from app.core.logger_config import (
    log_db_error,
    log_info,
    log_warning,
)

router = APIRouter(tags=["search"])


@router.get("/", response_model=List[BookResponse])
async def search_books(
    q: str = Query(..., min_length=3, description="Поисковый запрос (минимум 3 символа)"),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество результатов"),
    field: Optional[str] = Query(
        None, description="Поле для поиска (title, description или пусто для поиска по всем полям)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Полнотекстовый поиск книг по названию и описанию.
    Публичный эндпоинт, доступный без авторизации.

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
        log_info(f"Searching for: '{q}'{f' in field {field}' if field else ''}")

        books_service = BooksService(db)
        books = await books_service.search_books(q, limit, field)

        if not books:
            log_info(f"No books found for query: '{q}'")
            return []

        log_info(f"Found {len(books)} books for query: '{q}'")

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
        log_db_error(e, operation="search_books", query=q, field=field)
        raise SearchException("Ошибка при выполнении поиска")


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
        log_info(f"User {user.email} searching books by author: '{name}'")

        books_service = BooksService(db)
        books = await books_service.search_books_by_author(name, limit)

        if not books:
            log_info(f"No books found for author: '{name}'")
            return []

        log_info(f"Found {len(books)} books for author: '{name}'")

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
        log_db_error(e, operation="search_books_by_author", author=name)
        raise SearchException("Ошибка при выполнении поиска по автору")


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
        log_info(f"User {user.email} requesting suggestions for query: '{q}'")

        if not q or len(q.strip()) < 3:
            log_info("Query too short for suggestions")
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

        log_info(f"Found {len(suggestions)} suggestions for query: '{q}'")
        return suggestions

    except Exception as e:
        log_db_error(e, operation="suggest_corrections", query=q)
        raise SearchException("Ошибка при формировании подсказок для поиска")


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
        log_warning(f"User {user.email} attempting to update search vectors without admin rights")
        raise PermissionDeniedException(message="Требуются права администратора")

    try:
        log_info(f"User {user.email} updating search vectors")

        books_service = BooksService(db)
        count = await books_service.update_search_vectors()

        log_info(f"Search vectors updated for {count} books")
        return {"message": f"Поисковые векторы обновлены для {count} книг"}

    except Exception as e:
        log_db_error(e, operation="update_search_vectors")
        raise DatabaseException("Ошибка при обновлении поисковых векторов")


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
        log_warning(f"User {user.email} attempting to search by invalid field: {field_name}")
        raise InvalidSearchQueryException(
            message=f"Неверное поле для поиска. Допустимые поля: {', '.join(valid_fields)}"
        )

    try:
        log_info(f"User {user.email} searching by field {field_name}: '{q}'")

        books_service = BooksService(db)
        books = await books_service.search_by_field(field_name, q, limit)

        if not books:
            log_info(f"No books found for query '{q}' in field {field_name}")
            return []

        log_info(f"Found {len(books)} books for query '{q}' in field {field_name}")

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

    except InvalidSearchQueryException:
        raise
    except Exception as e:
        log_db_error(e, operation="search_by_field", field=field_name, query=q)
        raise SearchException("Ошибка при выполнении поиска по полю")


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
        log_info(
            f"User {user.email} performing advanced search with parameters: q='{q}', title='{title}', author='{author}', category='{category}', tag='{tag}'"
        )

        # Начинаем с общего поиска
        books_service = BooksService(db)
        books = await books_service.search_books(q, limit=100)  # Увеличиваем лимит для последующей фильтрации

        if not books:
            log_info(f"No books found for general query: '{q}'")
            return []

        # Фильтруем результаты по дополнительным критериям
        filtered_books = books

        # Фильтр по названию
        if title:
            title_lower = title.lower()
            filtered_books = [book for book in filtered_books if title_lower in book.title.lower()]
            log_info(f"After filtering by title '{title}' remaining {len(filtered_books)} books")

        # Фильтр по автору
        if author and filtered_books:
            author_lower = author.lower()
            filtered_books = [
                book for book in filtered_books if any(author_lower in a.name.lower() for a in book.authors)
            ]
            log_info(f"After filtering by author '{author}' remaining {len(filtered_books)} books")

        # Фильтр по категории
        if category and filtered_books:
            category_lower = category.lower()
            filtered_books = [
                book
                for book in filtered_books
                if any(category_lower in c.name_categories.lower() for c in book.categories)
            ]
            log_info(f"After filtering by category '{category}' remaining {len(filtered_books)} books")

        # Фильтр по тегу
        if tag and filtered_books:
            tag_lower = tag.lower()
            filtered_books = [
                book for book in filtered_books if any(tag_lower in t.name_tag.lower() for t in book.tags)
            ]
            log_info(f"After filtering by tag '{tag}' remaining {len(filtered_books)} books")

        # Ограничиваем количество результатов
        result_books = filtered_books[:limit]

        if not result_books:
            log_info("No books found after applying all filters")
            return []

        log_info(f"Found {len(result_books)} books for advanced query")

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
        log_db_error(e, operation="advanced_search", query=q, title=title, author=author, category=category, tag=tag)
        raise SearchException("Ошибка при выполнении расширенного поиска")
