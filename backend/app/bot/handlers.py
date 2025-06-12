"""
Обработчики команд и сообщений телеграм бота.
"""

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.core.logger_config import logger

from .api import BooksPortalAPI
from .keyboards import (
    get_authors_keyboard,
    get_books_keyboard,
    get_categories_keyboard,
    get_main_menu_keyboard,
    get_rating_keyboard,
)
from .states import BookSearch

router = Router()


def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков команд и сообщений"""

    # Обработчики команд
    dp.message.register(start_command, Command(commands=["start"]))
    dp.message.register(help_command, Command(commands=["help"]))
    dp.message.register(search_books_command, Command(commands=["search"]))

    # Обработчики состояний
    dp.message.register(process_search_query, BookSearch.waiting_for_query)

    # Обработчики основных действий
    dp.message.register(search_books_command, F.text == "📚 Поиск книг")
    dp.message.register(get_recommendations, F.text == "📖 Рекомендации")
    dp.message.register(show_categories, F.text == "📋 Категории")
    dp.message.register(show_authors, F.text == "👥 Авторы")

    # Обработчики callback-запросов
    dp.callback_query.register(process_book_callback, F.data.startswith("book_"))
    dp.callback_query.register(process_category_callback, F.data.startswith("category_"))
    dp.callback_query.register(process_author_callback, F.data.startswith("author_"))
    dp.callback_query.register(process_rating_callback, F.data.startswith("rate_"))
    dp.callback_query.register(process_pagination, F.data.startswith("books_page_"))

    dp.include_router(router)


async def start_command(message: Message):
    """Обработчик команды /start"""
    try:
        await message.answer(
            "Добро пожаловать в Books Portal! 📚\n" "Я помогу вам найти интересные книги и получить рекомендации.",
            reply_markup=get_main_menu_keyboard(),
        )
        logger.info(f"User {message.from_user.id} started the bot")
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


async def help_command(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "📚 Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/search - Поиск книг\n\n"
        "Основные функции:\n"
        "• 📚 Поиск книг - поиск по каталогу\n"
        "• 📖 Рекомендации - персонализированные рекомендации\n"
        "• 📋 Категории - просмотр категорий\n"
        "• 👥 Авторы - просмотр авторов\n\n"
        "Для оценки книг используйте кнопки со звездочками ⭐"
    )
    await message.answer(help_text, reply_markup=get_main_menu_keyboard())


async def search_books_command(message: Message, state: FSMContext):
    """Обработчик команды поиска книг"""
    try:
        await message.answer("Введите название книги или автора для поиска:")
        await state.set_state(BookSearch.waiting_for_query)
    except Exception as e:
        logger.error(f"Error in search command: {str(e)}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


async def process_search_query(message: Message, state: FSMContext):
    """Обработчик поискового запроса"""
    try:
        query = message.text.strip()
        if not query:
            await message.answer("Пожалуйста, введите поисковый запрос.")
            return

        async with BooksPortalAPI() as api:
            results = await api.search_books(query=query, page=1, limit=5)

            if not results or not results.get("items"):
                await message.answer("По вашему запросу ничего не найдено.")
                return

            response = "📚 Результаты поиска:\n\n"
            for book in results["items"]:
                response += (
                    f"📖 {book['title']}\n"
                    f"👤 Авторы: {', '.join([author['name'] for author in book.get('authors', [])])}\n"
                    f"⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n\n"
                )

            keyboard = get_books_keyboard(results["items"])
            await message.answer(response, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        await message.answer("Произошла ошибка при поиске. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()


async def get_recommendations(message: Message):
    """Обработчик получения рекомендаций"""
    try:
        async with BooksPortalAPI() as api:
            recommendations = await api.get_recommendations(limit=5)

            if not recommendations:
                await message.answer("К сожалению, не удалось получить рекомендации.")
                return

            response = "📖 Рекомендуемые книги:\n\n"
            for book in recommendations:
                response += (
                    f"📖 {book['title']}\n"
                    f"👤 Авторы: {', '.join([author['name'] for author in book.get('authors', [])])}\n"
                    f"⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n\n"
                )

            keyboard = get_books_keyboard(recommendations)
            await message.answer(response, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        await message.answer("Произошла ошибка при получении рекомендаций. Пожалуйста, попробуйте позже.")


async def show_categories(message: Message):
    """Обработчик показа категорий"""
    try:
        async with BooksPortalAPI() as api:
            categories = await api.get_categories()

            if not categories:
                await message.answer("Категории не найдены.")
                return

            response = "📋 Доступные категории:\n\n"
            for category in categories:
                response += f"• {category['name']}\n"

            keyboard = get_categories_keyboard(categories)
            await message.answer(response, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error showing categories: {str(e)}")
        await message.answer("Произошла ошибка при получении категорий. Пожалуйста, попробуйте позже.")


async def show_authors(message: Message):
    """Обработчик показа авторов"""
    try:
        async with BooksPortalAPI() as api:
            authors = await api.get_authors()

            if not authors:
                await message.answer("Авторы не найдены.")
                return

            response = "👥 Доступные авторы:\n\n"
            for author in authors:
                response += f"• {author['name']}\n"

            keyboard = get_authors_keyboard(authors)
            await message.answer(response, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error showing authors: {str(e)}")
        await message.answer("Произошла ошибка при получении авторов. Пожалуйста, попробуйте позже.")


async def process_book_callback(callback: CallbackQuery):
    """Обработчик callback для книг"""
    try:
        book_id = int(callback.data.split("_")[1])
        async with BooksPortalAPI() as api:
            book = await api.get_book(book_id)

            if not book:
                await callback.answer("Книга не найдена.")
                return

            response = (
                f"📖 {book['title']}\n\n"
                f"👤 Авторы: {', '.join([author['name'] for author in book.get('authors', [])])}\n"
                f"📋 Категории: {', '.join([cat['name'] for cat in book.get('categories', [])])}\n"
                f"⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n"
                f"📝 Описание: {book.get('description', 'Нет описания')}\n"
            )

            keyboard = get_rating_keyboard(book_id)
            await callback.message.answer(response, reply_markup=keyboard)
            await callback.answer()

    except Exception as e:
        logger.error(f"Error processing book callback: {str(e)}")
        await callback.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


async def process_category_callback(callback: CallbackQuery):
    """Обработчик callback для категорий"""
    try:
        category_id = int(callback.data.split("_")[1])
        async with BooksPortalAPI() as api:
            books = await api.get_books_by_category(category_id, page=1, limit=5)

            if not books or not books.get("items"):
                await callback.answer("Книги в этой категории не найдены.")
                return

            response = "📚 Книги в категории:\n\n"
            for book in books["items"]:
                response += (
                    f"📖 {book['title']}\n"
                    f"👤 Авторы: {', '.join([author['name'] for author in book.get('authors', [])])}\n"
                    f"⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n\n"
                )

            keyboard = get_books_keyboard(books["items"])
            await callback.message.answer(response, reply_markup=keyboard)
            await callback.answer()

    except Exception as e:
        logger.error(f"Error processing category callback: {str(e)}")
        await callback.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


async def process_author_callback(callback: CallbackQuery):
    """Обработчик callback для авторов"""
    try:
        author_id = int(callback.data.split("_")[1])
        async with BooksPortalAPI() as api:
            books = await api.get_books_by_author(author_id, page=1, limit=5)

            if not books or not books.get("items"):
                await callback.answer("Книги этого автора не найдены.")
                return

            response = "📚 Книги автора:\n\n"
            for book in books["items"]:
                response += f"📖 {book['title']}\n" f"⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n\n"

            keyboard = get_books_keyboard(books["items"])
            await callback.message.answer(response, reply_markup=keyboard)
            await callback.answer()

    except Exception as e:
        logger.error(f"Error processing author callback: {str(e)}")
        await callback.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")


async def process_rating_callback(callback: CallbackQuery):
    """Обработчик callback для оценки книг"""
    try:
        _, book_id, rating = callback.data.split("_")
        book_id = int(book_id)
        rating = int(rating)

        async with BooksPortalAPI() as api:
            success = await api.rate_book(book_id, rating)

            if success:
                await callback.answer(f"Спасибо за вашу оценку: {rating} ⭐")
            else:
                await callback.answer("Не удалось сохранить оценку.")

    except Exception as e:
        logger.error(f"Error processing rating callback: {str(e)}")
        await callback.answer("Произошла ошибка при сохранении оценки.")


async def process_pagination(callback: CallbackQuery):
    """Обработчик пагинации"""
    try:
        page = int(callback.data.split("_")[-1])
        async with BooksPortalAPI() as api:
            books = await api.get_books(page=page, limit=5)

            if not books or not books.get("items"):
                await callback.answer("Больше книг не найдено.")
                return

            response = f"📚 Страница {page}:\n\n"
            for book in books["items"]:
                response += (
                    f"📖 {book['title']}\n"
                    f"👤 Авторы: {', '.join([author['name'] for author in book.get('authors', [])])}\n"
                    f"⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n\n"
                )

            keyboard = get_books_keyboard(books["items"], page)
            await callback.message.edit_text(response, reply_markup=keyboard)
            await callback.answer()

    except Exception as e:
        logger.error(f"Error processing pagination: {str(e)}")
        await callback.answer("Произошла ошибка при загрузке страницы.")
