from aiogram.fsm.state import State, StatesGroup


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


class SearchBooks(StatesGroup):
    """Состояния для поиска книг"""

    waiting_for_query = State()
