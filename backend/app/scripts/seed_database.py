import asyncio
import json
import sys
from pathlib import Path

from fastapi_users.password import PasswordHelper
from models import Author, Book, Category, Tag, User
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine

# Добавляем путь к корню проекта
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Создаем экземпляр PasswordHelper
password_helper = PasswordHelper()


async def create_or_get_author(db: AsyncSession, author_data: dict) -> Author:
    try:
        # Проверяем наличие необходимых полей
        if "name" not in author_data:
            print("Пропущен автор: отсутствует поле 'name'")
            return None

        author = Author(name=author_data["name"])
        db.add(author)
        await db.commit()
        await db.refresh(author)
        return author
    except IntegrityError:
        await db.rollback()
        # Если автор уже существует, получаем его из базы
        stmt = select(Author).where(Author.name == author_data["name"])
        result = await db.execute(stmt)
        existing_author = result.scalar_one_or_none()
        return existing_author
    except Exception as e:
        print(f"Ошибка при создании автора {author_data.get('name', 'Unknown')}: {str(e)}")
        await db.rollback()
        return None


async def create_or_get_category(db: AsyncSession, category_data: dict) -> Category:
    try:
        # Проверяем наличие необходимых полей
        if "name_categories" not in category_data:
            print("Пропущена категория: отсутствует поле 'name_categories'")
            return None

        category = Category(
            name_categories=category_data["name_categories"],
            description=category_data.get("description", ""),
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
    except IntegrityError:
        await db.rollback()
        # Если категория уже существует, получаем её из базы
        stmt = select(Category).where(Category.name_categories == category_data["name_categories"])
        result = await db.execute(stmt)
        existing_category = result.scalar_one_or_none()
        return existing_category
    except Exception as e:
        print(f"Ошибка при создании категории {category_data.get('name_categories', 'Unknown')}: {str(e)}")
        await db.rollback()
        return None


async def create_or_get_tag(db: AsyncSession, tag_data: dict) -> Tag:
    try:
        # Проверяем наличие необходимых полей
        if "name_tag" not in tag_data:
            print("Пропущен тег: отсутствует поле 'name_tag'")
            return None

        tag = Tag(name_tag=tag_data["name_tag"])
        db.add(tag)
        await db.commit()
        await db.refresh(tag)
        return tag
    except IntegrityError:
        await db.rollback()
        # Если тег уже существует, получаем его из базы
        stmt = select(Tag).where(Tag.name_tag == tag_data["name_tag"])
        result = await db.execute(stmt)
        existing_tag = result.scalar_one_or_none()
        return existing_tag
    except Exception as e:
        print(f"Ошибка при создании тега {tag_data.get('name_tag', 'Unknown')}: {str(e)}")
        await db.rollback()
        return None


async def get_author_by_id(db: AsyncSession, author_id: int) -> Author:
    stmt = select(Author).where(Author.id == author_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_category_by_id(db: AsyncSession, category_id: int) -> Category:
    stmt = select(Category).where(Category.id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_tag_by_id(db: AsyncSession, tag_id: int) -> Tag:
    stmt = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def seed_database():
    # Получаем путь к файлу с данными
    current_dir = Path(__file__).parent
    data_file = current_dir / "data" / "seed_data.json"

    print(f"Ищем файл по пути: {data_file}")
    print(f"Текущая директория: {current_dir}")

    # Проверяем существование файла
    if not data_file.exists():
        print(f"Файл {data_file} не найден!")
        print("Убедитесь, что файл seed_data.json находится в директории backend/app/scripts/data/")
        return

    # Читаем данные из JSON файла
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Ошибка при чтении JSON файла: {str(e)}")
        return
    except Exception as e:
        print(f"Ошибка при открытии файла: {str(e)}")
        return

    # Получаем сессию базы данных
    try:
        async with AsyncSessionLocal() as db:
            # Создаем пользователей
            for user_data in data.get("users", []):
                try:
                    user = User(
                        email=user_data["email"],
                        hashed_password=password_helper.hash(user_data["password"]),
                    )
                    db.add(user)
                    await db.commit()
                except IntegrityError:
                    await db.rollback()
                    print(f"Пользователь с email {user_data['email']} уже существует")
            print("Пользователи обработаны")

            # Создаем авторов
            authors = []
            for author_data in data.get("authors", []):
                author = await create_or_get_author(db, author_data)
                if author:
                    authors.append(author)
            print("Авторы обработаны")

            # Создаем категории
            categories = []
            for category_data in data.get("categories", []):
                category = await create_or_get_category(db, category_data)
                if category:
                    categories.append(category)
            print("Категории обработаны")

            # Создаем теги
            tags = []
            for tag_data in data.get("tags", []):
                tag = await create_or_get_tag(db, tag_data)
                if tag:
                    tags.append(tag)
            print("Теги обработаны")

            # Создаем книги
            for book_data in data.get("books", []):
                try:
                    # Проверяем наличие необходимых полей
                    required_fields = [
                        "title",
                        "year",
                        "publisher",
                        "isbn",
                        "description",
                        "cover",
                        "language",
                        "file_url",
                    ]
                    missing_fields = [field for field in required_fields if field not in book_data]
                    if missing_fields:
                        print(f"Пропущена книга: отсутствуют поля {', '.join(missing_fields)}")
                        continue

                    # Получаем связанные объекты
                    book_authors = []
                    for author_id in book_data.pop("authors", []):
                        author = await get_author_by_id(db, author_id)
                        if author:
                            book_authors.append(author)

                    book_categories = []
                    for category_id in book_data.pop("categories", []):
                        category = await get_category_by_id(db, category_id)
                        if category:
                            book_categories.append(category)

                    book_tags = []
                    for tag_id in book_data.pop("tags", []):
                        tag = await get_tag_by_id(db, tag_id)
                        if tag:
                            book_tags.append(tag)

                    # Создаем книгу
                    book = Book(
                        title=book_data["title"],
                        year=book_data["year"],
                        publisher=book_data["publisher"],
                        isbn=book_data["isbn"],
                        description=book_data["description"],
                        cover=book_data["cover"],
                        language=book_data["language"].lower(),
                        file_url=book_data["file_url"],
                    )
                    book.authors = book_authors
                    book.categories = book_categories
                    book.tags = book_tags
                    db.add(book)
                    await db.commit()
                    await db.refresh(book)
                except IntegrityError:
                    await db.rollback()
                    print(f"Книга '{book_data.get('title', 'Unknown')}' уже существует")
                except Exception as e:
                    print(f"Ошибка при создании книги '{book_data.get('title', 'Unknown')}': {str(e)}")
                    await db.rollback()
            print("Книги обработаны")

            print("База данных успешно заполнена!")

    except Exception as e:
        print(f"Ошибка при заполнении базы данных: {str(e)}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
