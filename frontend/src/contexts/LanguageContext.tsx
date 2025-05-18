import React, { createContext, useContext, useState, useEffect } from 'react';

type Language = 'ru' | 'en';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: keyof typeof translations['ru']) => string;
}

const translations = {
  ru: {
    // Общие
    'app.name': 'Книжный Портал',
    'app.loading': 'Загрузка...',
    'app.error': 'Ошибка',
    'app.success': 'Успешно',
    'app.warning': 'Предупреждение',
    'app.info': 'Информация',
    'app.close': 'Закрыть',
    'app.save': 'Сохранить',
    'app.cancel': 'Отмена',
    'app.delete': 'Удалить',
    'app.edit': 'Редактировать',
    'app.create': 'Создать',
    'app.search': 'Поиск',
    'app.filter': 'Фильтр',
    'app.sort': 'Сортировка',
    'app.pagination.previous': 'Предыдущая',
    'app.pagination.next': 'Следующая',
    'app.pagination.page': 'Страница',
    'app.pagination.of': 'из',

    // Навигация
    'nav.home': 'Главная',
    'nav.books': 'Книги',
    'nav.authors': 'Авторы',
    'nav.categories': 'Категории',
    'nav.admin': 'Админ панель',
    'nav.profile': 'Профиль',
    'nav.login': 'Войти',
    'nav.register': 'Регистрация',
    'nav.logout': 'Выйти',

    // Авторизация
    'auth.login.title': 'Вход в систему',
    'auth.login.email': 'Email',
    'auth.login.password': 'Пароль',
    'auth.login.submit': 'Войти',
    'auth.login.noAccount': 'Нет аккаунта? Зарегистрируйтесь',
    'auth.register.title': 'Регистрация',
    'auth.register.username': 'Имя пользователя',
    'auth.register.email': 'Email',
    'auth.register.password': 'Пароль',
    'auth.register.confirmPassword': 'Подтвердите пароль',
    'auth.register.submit': 'Зарегистрироваться',
    'auth.register.hasAccount': 'Уже есть аккаунт? Войдите',

    // Книги
    'books.add': 'Добавить книгу',
    'books.edit': 'Редактировать книгу',
    'books.delete': 'Удалить книгу',
    'books.author': 'Автор',
    'books.category': 'Категория',
    'books.description': 'Описание',
    'books.publicationDate': 'Дата публикации',
    'books.isbn': 'ISBN',
    'books.pages': 'Страницы',
    'books.price': 'Цена',
    'books.cover': 'Обложка',
    'books.noBooks': 'Книги не найдены',

    // Авторы
    'authors.title': 'Авторы',
    'authors.add': 'Добавить автора',
    'authors.edit': 'Редактировать автора',
    'authors.delete': 'Удалить автора',
    'authors.name': 'Имя',
    'authors.biography': 'Биография',
    'authors.birthDate': 'Дата рождения',
    'authors.deathDate': 'Дата смерти',
    'authors.noAuthors': 'Авторы не найдены',

    // Категории
    'categories.title': 'Категории',
    'categories.add': 'Добавить категорию',
    'categories.edit': 'Редактировать категорию',
    'categories.delete': 'Удалить категорию',
    'categories.name': 'Название',
    'categories.description': 'Описание',
    'categories.noCategories': 'Категории не найдены',

    // Ошибки
    'error.required': 'Обязательное поле',
    'error.email': 'Некорректный email',
    'error.password': 'Пароль должен содержать минимум 6 символов',
    'error.passwordMatch': 'Пароли не совпадают',
    'error.server': 'Ошибка сервера',
    'error.notFound': 'Не найдено',
    'error.unauthorized': 'Не авторизован',
    'error.forbidden': 'Доступ запрещен',
  },
  en: {
    // General
    'app.name': 'Books Portal',
    'app.loading': 'Loading...',
    'app.error': 'Error',
    'app.success': 'Success',
    'app.warning': 'Warning',
    'app.info': 'Information',
    'app.close': 'Close',
    'app.save': 'Save',
    'app.cancel': 'Cancel',
    'app.delete': 'Delete',
    'app.edit': 'Edit',
    'app.create': 'Create',
    'app.search': 'Search',
    'app.filter': 'Filter',
    'app.sort': 'Sort',
    'app.pagination.previous': 'Previous',
    'app.pagination.next': 'Next',
    'app.pagination.page': 'Page',
    'app.pagination.of': 'of',

    // Navigation
    'nav.home': 'Home',
    'nav.books': 'Books',
    'nav.authors': 'Authors',
    'nav.categories': 'Categories',
    'nav.admin': 'Admin Panel',
    'nav.profile': 'Profile',
    'nav.login': 'Login',
    'nav.register': 'Register',
    'nav.logout': 'Logout',

    // Authentication
    'auth.login.title': 'Login',
    'auth.login.email': 'Email',
    'auth.login.password': 'Password',
    'auth.login.submit': 'Login',
    'auth.login.noAccount': 'No account? Register',
    'auth.register.title': 'Register',
    'auth.register.username': 'Username',
    'auth.register.email': 'Email',
    'auth.register.password': 'Password',
    'auth.register.confirmPassword': 'Confirm Password',
    'auth.register.submit': 'Register',
    'auth.register.hasAccount': 'Already have an account? Login',

    // Books
    'books.add': 'Add Book',
    'books.edit': 'Edit Book',
    'books.delete': 'Delete Book',
    'books.author': 'Author',
    'books.category': 'Category',
    'books.description': 'Description',
    'books.publicationDate': 'Publication Date',
    'books.isbn': 'ISBN',
    'books.pages': 'Pages',
    'books.price': 'Price',
    'books.cover': 'Cover',
    'books.noBooks': 'No books found',

    // Authors
    'authors.title': 'Authors',
    'authors.add': 'Add Author',
    'authors.edit': 'Edit Author',
    'authors.delete': 'Delete Author',
    'authors.name': 'Name',
    'authors.biography': 'Biography',
    'authors.birthDate': 'Birth Date',
    'authors.deathDate': 'Death Date',
    'authors.noAuthors': 'No authors found',

    // Categories
    'categories.title': 'Categories',
    'categories.add': 'Add Category',
    'categories.edit': 'Edit Category',
    'categories.delete': 'Delete Category',
    'categories.name': 'Name',
    'categories.description': 'Description',
    'categories.noCategories': 'No categories found',

    // Errors
    'error.required': 'Required field',
    'error.email': 'Invalid email',
    'error.password': 'Password must be at least 6 characters',
    'error.passwordMatch': 'Passwords do not match',
    'error.server': 'Server error',
    'error.notFound': 'Not found',
    'error.unauthorized': 'Unauthorized',
    'error.forbidden': 'Forbidden',
  },
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguage] = useState<Language>(() => {
    const savedLanguage = localStorage.getItem('language');
    return (savedLanguage as Language) || 'ru';
  });

  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  const t = (key: keyof typeof translations['ru']): string => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
