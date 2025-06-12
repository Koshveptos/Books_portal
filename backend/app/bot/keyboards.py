"""
Клавиатуры для телеграм бота.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает основное меню бота
    """
    keyboard = [
        [KeyboardButton(text="📚 Поиск книг")],
        [KeyboardButton(text="📖 Рекомендации")],
        [KeyboardButton(text="📋 Категории")],
        [KeyboardButton(text="👥 Авторы")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, input_field_placeholder="Выберите действие")


def get_books_keyboard(books: list = None, page: int = 1) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру со списком книг
    """
    keyboard = []
    if books:
        for book in books:
            keyboard.append(
                [InlineKeyboardButton(text=f"{book['title']} - {book['author']}", callback_data=f"book_{book['id']}")]
            )

    # Добавляем навигацию
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"books_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}", callback_data="current_page"))
    nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"books_page_{page+1}"))
    keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_categories_keyboard(categories: list = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру со списком категорий
    """
    keyboard = []
    if categories:
        for category in categories:
            keyboard.append([InlineKeyboardButton(text=category["name"], callback_data=f"category_{category['id']}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_authors_keyboard(authors: list = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру со списком авторов
    """
    keyboard = []
    if authors:
        for author in authors:
            keyboard.append([InlineKeyboardButton(text=author["name"], callback_data=f"author_{author['id']}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_rating_keyboard(book_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для оценки книги
    """
    keyboard = []
    for rating in range(1, 6):
        keyboard.append([InlineKeyboardButton(text="⭐" * rating, callback_data=f"rate_{book_id}_{rating}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
