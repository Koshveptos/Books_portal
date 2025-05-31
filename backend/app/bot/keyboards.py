from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура бота"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Поиск книг"), KeyboardButton(text="📚 Каталог")],
            [KeyboardButton(text="👤 Привязать аккаунт"), KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_link_account_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для привязки аккаунта"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Привязать аккаунт", callback_data="link_account")],
            [InlineKeyboardButton(text="🌐 Перейти на сайт", url="https://books-portal.ru")],
        ]
    )
    return keyboard


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="confirm"),
                InlineKeyboardButton(text="❌ Нет", callback_data="cancel"),
            ]
        ]
    )
    return keyboard


def get_pagination_keyboard(current_page: int, total_pages: int, action: str) -> InlineKeyboardMarkup:
    """Клавиатура пагинации"""
    keyboard = []

    # Кнопки навигации
    nav_buttons = []

    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{action}_page_{current_page - 1}"))

    nav_buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="ignore"))

    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{action}_page_{current_page + 1}"))

    keyboard.append(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_book_actions_keyboard(book_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с книгой"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📖 Подробнее", callback_data=f"book_details_{book_id}"),
                InlineKeyboardButton(text="👤 Авторы", callback_data=f"book_authors_{book_id}"),
            ],
            [
                InlineKeyboardButton(text="📚 Похожие", callback_data=f"similar_books_{book_id}"),
                InlineKeyboardButton(text="⭐ Оценить", callback_data=f"rate_book_{book_id}"),
            ],
            [InlineKeyboardButton(text="❤️ В избранное", callback_data=f"add_favorite_{book_id}")],
        ]
    )
    return keyboard


def get_rating_keyboard(book_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для оценки книги"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐", callback_data=f"rating_{book_id}_1"),
                InlineKeyboardButton(text="⭐⭐", callback_data=f"rating_{book_id}_2"),
                InlineKeyboardButton(text="⭐⭐⭐", callback_data=f"rating_{book_id}_3"),
                InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"rating_{book_id}_4"),
                InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"rating_{book_id}_5"),
            ]
        ]
    )
    return keyboard
