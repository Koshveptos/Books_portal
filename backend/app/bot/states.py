"""
Состояния для FSM (Finite State Machine) телеграм бота.
"""

from aiogram.fsm.state import State, StatesGroup


class BookSearch(StatesGroup):
    """Состояния для поиска книг"""

    waiting_for_query = State()  # Ожидание поискового запроса


class BookRating(StatesGroup):
    """Состояния для оценки книг"""

    waiting_for_rating = State()  # Ожидание оценки книги


class CategorySelection(StatesGroup):
    """Состояния для выбора категории"""

    waiting_for_category = State()  # Ожидание выбора категории


class AuthorSelection(StatesGroup):
    """Состояния для выбора автора"""

    waiting_for_author = State()  # Ожидание выбора автора


class LinkAccount(StatesGroup):
    """Состояния для процесса привязки аккаунта"""

    waiting_for_email = State()  # Ожидание email
    waiting_for_password = State()  # Ожидание пароля
    waiting_for_confirmation = State()  # Ожидание подтверждения


class Registration(StatesGroup):
    """Состояния для процесса регистрации"""

    waiting_for_email = State()  # Ожидание email
    waiting_for_password = State()  # Ожидание пароля
    waiting_for_password_confirmation = State()  # Ожидание подтверждения пароля
