import logging

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .api import BooksPortalAPI
from .keyboards import (
    get_book_actions_keyboard,
    get_main_keyboard,
    get_pagination_keyboard,
    get_rating_keyboard,
)
from .states import SearchBooks

logger = logging.getLogger(__name__)
router = Router()


def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков команд и сообщений"""

    # Обработчики команд
    dp.message.register(start_command, Command(commands=["start"]))
    dp.message.register(help_command, Command(commands=["help"]))
    dp.message.register(search_books_command, Command(commands=["search"]))

    # Обработчики состояний
    dp.message.register(process_search_query, SearchBooks.waiting_for_query)

    # Обработчики основных действий
    dp.message.register(show_catalog, lambda msg: msg.text == "📚 Каталог")
    dp.message.register(search_books_command, lambda msg: msg.text == "🔍 Поиск книг")
    dp.message.register(show_link_account, lambda msg: msg.text == "👤 Привязать аккаунт")

    # Обработчики callback-запросов
    dp.callback_query.register(process_link_account, F.data == "link_account")
    dp.callback_query.register(
        process_book_action,
        F.data.startswith(("book_authors_", "similar_books_", "book_details_", "rate_book_", "add_favorite_")),
    )
    dp.callback_query.register(process_pagination, F.data.endswith(("_page_")))


async def start_command(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "Добро пожаловать в Books Portal Bot! 📚\n\n"
        "Я помогу вам найти интересные книги и получить персонализированные рекомендации.\n\n"
        "Вы можете:\n"
        "• 🔍 Искать книги\n"
        "• 📚 Просматривать каталог\n"
        "• 📖 Читать описания книг\n\n"
        "Для доступа к дополнительным функциям (рекомендации, избранное, оценки) "
        "привяжите свой аккаунт с сайта Books Portal.",
        reply_markup=get_main_keyboard(),
    )


async def help_command(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "📚 Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/search - Поиск книг\n\n"
        "Основные функции:\n"
        "• 🔍 Поиск книг - поиск по каталогу\n"
        "• 📚 Каталог - просмотр всех книг\n"
        "• 📖 Описания - информация о книгах\n\n"
        "Для доступа к дополнительным функциям:\n"
        "• 📚 Мои книги - ваша библиотека\n"
        "• 📖 Рекомендации - персонализированные рекомендации\n"
        "• ⭐ Оценки - ваши оценки книг\n"
        "• ❤️ Избранное - ваши избранные книги\n\n"
        "Привяжите аккаунт с сайта для доступа к дополнительным функциям!"
    )
    await message.answer(help_text)


async def process_link_account(callback: CallbackQuery):
    """Обработчик кнопки привязки аккаунта"""
    await callback.message.answer(
        "Для привязки аккаунта:\n\n"
        "1. Перейдите на сайт Books Portal:\n"
        "http://localhost:3000\n\n"
        "2. Войдите в свой аккаунт или зарегистрируйтесь\n"
        "3. В личном кабинете найдите раздел 'Привязать Telegram'\n"
        "4. Введите ваш Telegram ID: " + str(callback.from_user.id) + "\n\n"
        "После привязки аккаунта вы получите доступ ко всем функциям бота!"
    )
    await callback.answer()


async def search_books_command(message: Message, state: FSMContext):
    """Обработчик команды /search"""
    await message.answer("Введите название книги или автора для поиска:")
    await state.set_state(SearchBooks.waiting_for_query)


async def process_search_query(message: Message, state: FSMContext):
    """Обработчик поискового запроса"""
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите поисковый запрос.")
        return

    try:
        async with BooksPortalAPI() as api:
            # Получаем результаты поиска с меньшим количеством книг
            results = await api.search_books(query=query, page=1, limit=3)

            if not results or not results.get("items"):
                await message.answer("По вашему запросу ничего не найдено.")
                return

            # Сохраняем поисковый запрос в состоянии
            await state.update_data(search_query=query)

            # Формируем сообщение с результатами
            response = "📚 Результаты поиска:\n\n"
            for i, book in enumerate(results["items"], 1):
                # Получаем список авторов
                authors = await api.get_book_authors(book["id"])
                authors_str = ", ".join([author["name"] for author in authors]) if authors else "Не указан"

                response += (
                    f"{i}. 📖 {book['title']}\n"
                    f"   👤 Авторы: {authors_str}\n"
                    f"   📚 Категории: {', '.join([cat['name_categories'] for cat in book.get('categories', [])]) if book.get('categories') else 'Не указаны'}\n"
                    f"   ⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n"
                    f"   📝 Описание: {book.get('description', 'Нет описания')[:100]}...\n\n"
                )

            # Добавляем пагинацию только если есть больше одной страницы
            if results["total"] > results["size"]:
                total_pages = (results["total"] + results["size"] - 1) // results["size"]
                keyboard = get_pagination_keyboard(1, total_pages, "search")
                await message.answer(response, reply_markup=keyboard)
            else:
                await message.answer(response)

            # Добавляем кнопки действий для каждой книги
            for book in results["items"]:
                keyboard = get_book_actions_keyboard(book["id"])
                await message.answer(f"Действия с книгой '{book['title']}':", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        await message.answer("Произошла ошибка при поиске. Пожалуйста, попробуйте позже.")

    await state.clear()


async def show_catalog(message: Message):
    """Показать каталог книг"""
    try:
        async with BooksPortalAPI() as api:
            # Получаем первую страницу каталога с меньшим количеством книг
            books = await api.get_catalog(page=1, limit=3)

            if not books or not isinstance(books, dict) or not books.get("items"):
                await message.answer("Каталог пуст.")
                return

            # Формируем сообщение
            response = "📚 Каталог книг:\n\n"
            for i, book in enumerate(books["items"], 1):
                # Получаем список авторов
                authors = await api.get_book_authors(book["id"])
                authors_str = ", ".join([author["name"] for author in authors]) if authors else "Не указан"

                response += (
                    f"{i}. 📖 {book['title']}\n"
                    f"   👤 Авторы: {authors_str}\n"
                    f"   ⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n"
                    f"   📝 Описание: {book.get('description', 'Нет описания')[:100]}...\n\n"
                )

            # Добавляем пагинацию
            total_pages = (books["total"] + 2) // 3  # Округляем вверх
            keyboard = get_pagination_keyboard(1, total_pages, "catalog")

            await message.answer(response, reply_markup=keyboard)

            # Добавляем кнопки действий для каждой книги
            for book in books["items"]:
                keyboard = get_book_actions_keyboard(book["id"])
                await message.answer(f"Действия с книгой '{book['title']}':", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error getting catalog: {str(e)}")
        await message.answer("Произошла ошибка при загрузке каталога. Пожалуйста, попробуйте позже.")


async def show_link_account(message: Message):
    """Показать информацию о привязке аккаунта"""
    try:
        async with BooksPortalAPI() as api:
            # Проверяем, привязан ли уже аккаунт
            user_info = await api.get_user_info(message.from_user.id)
            if user_info and user_info.get("telegram_id") == message.from_user.id:
                await message.answer(
                    "✅ Ваш аккаунт уже привязан!\n\n"
                    "Теперь вам доступны все функции бота:\n"
                    "• 📚 Мои книги\n"
                    "• 📖 Рекомендации\n"
                    "• ⭐ Оценки\n"
                    "• ❤️ Избранное"
                )
                return
    except Exception:
        pass  # Игнорируем ошибку, если пользователь не привязан

    await message.answer(
        "Для привязки аккаунта:\n\n"
        "1. Перейдите на сайт Books Portal:\n"
        "http://localhost:8000\n\n"
        "2. Войдите в свой аккаунт или зарегистрируйтесь\n"
        "3. В личном кабинете найдите раздел 'Привязать Telegram'\n"
        "4. Введите ваш Telegram ID: " + str(message.from_user.id) + "\n\n"
        "После привязки аккаунта вы получите доступ ко всем функциям бота!"
    )


async def process_book_action(callback: CallbackQuery):
    """Обработчик действий с книгой"""
    try:
        action, book_id = callback.data.split("_", 1)
        book_id = int(book_id)

        async with BooksPortalAPI() as api:
            if action == "book_details":
                # Получаем детальную информацию о книге
                book = await api.get_book_details(book_id)
                authors = await api.get_book_authors(book_id)
                authors_str = ", ".join([author["name"] for author in authors]) if authors else "Не указан"

                response = (
                    f"📖 {book['title']}\n\n"
                    f"👤 Авторы: {authors_str}\n"
                    f"📚 Категории: {', '.join([cat['name_categories'] for cat in book.get('categories', [])]) if book.get('categories') else 'Не указаны'}\n"
                    f"⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n"
                    f"📝 Описание: {book.get('description', 'Нет описания')}\n"
                )
                await callback.message.answer(response)

            elif action == "book_authors":
                # Получаем список авторов
                authors = await api.get_book_authors(book_id)
                if authors:
                    response = "👤 Авторы книги:\n\n"
                    for author in authors:
                        response += f"• {author['name']}\n"
                else:
                    response = "Авторы не указаны"
                await callback.message.answer(response)

            elif action == "similar_books":
                # Получаем похожие книги
                similar_books = await api.get_similar_books(book_id)
                if similar_books:
                    response = "📚 Похожие книги:\n\n"
                    for i, book in enumerate(similar_books, 1):
                        response += f"{i}. {book['title']}\n"
                else:
                    response = "Похожие книги не найдены"
                await callback.message.answer(response)

            elif action == "rate_book":
                # Показываем клавиатуру для оценки
                keyboard = get_rating_keyboard(book_id)
                await callback.message.answer("Оцените книгу:", reply_markup=keyboard)

            elif action == "add_favorite":
                # Добавляем книгу в избранное
                result = await api.toggle_favorite(book_id)
                if result.get("is_favorite"):
                    await callback.message.answer("✅ Книга добавлена в избранное")
                else:
                    await callback.message.answer("❌ Книга удалена из избранного")

    except Exception as e:
        logger.error(f"Error processing book action: {str(e)}")
        await callback.message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

    await callback.answer()


async def process_pagination(callback: CallbackQuery, state: FSMContext):
    """Обработчик пагинации"""
    action, page = callback.data.split("_page_")
    page = int(page)

    try:
        async with BooksPortalAPI() as api:
            if action == "search":
                # Получаем сохраненный поисковый запрос
                data = await state.get_data()
                query = data.get("search_query", "")

                # Получаем результаты поиска для указанной страницы
                results = await api.search_books(query=query, page=page, limit=3)
                response = "📚 Результаты поиска:\n\n"
                for i, book in enumerate(results["items"], 1):
                    response += (
                        f"{i}. 📖 {book['title']}\n"
                        f"   👤 Автор: {book.get('author', 'Не указан')}\n"
                        f"   ⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n\n"
                    )
                total_pages = (results["total"] + 2) // 3
            elif action == "catalog":
                # Получаем книги каталога для указанной страницы
                books = await api.get_catalog(page=page, limit=3)
                response = "📚 Каталог книг:\n\n"
                for i, book in enumerate(books["items"], 1):
                    response += (
                        f"{i}. 📖 {book['title']}\n"
                        f"   👤 Автор: {book.get('author', 'Не указан')}\n"
                        f"   ⭐ Рейтинг: {book.get('rating', 'Нет оценок')}\n\n"
                    )
                total_pages = (books["total"] + 2) // 3

            # Обновляем пагинацию
            keyboard = get_pagination_keyboard(page, total_pages, action)

            await callback.message.edit_text(response, reply_markup=keyboard)

    except Exception as e:
        await callback.message.answer(f"Произошла ошибка при загрузке страницы: {str(e)}")

    await callback.answer()
