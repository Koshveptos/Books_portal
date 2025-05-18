import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

// Компонент для административной панели
const AdminPage: React.FC = () => {
  const { user, hasRole } = useAuth();
  const [activeTab, setActiveTab] = useState<string>('users');

  // Проверка прав администратора (дополнительная проверка)
  if (!hasRole('admin')) {
    return (
      <div className="text-center p-8">
        <h1 className="text-red-600 text-xl font-bold">Доступ запрещен</h1>
        <p className="mt-4">У вас нет прав администратора для просмотра этой страницы.</p>
      </div>
    );
  }

  // Рендеринг панели администратора
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Панель администратора</h1>

      {/* Табы для навигации */}
      <div className="border-b border-gray-200 mb-6">
        <ul className="flex -mb-px">
          <li className="mr-2">
            <button
              className={`inline-block py-2 px-4 border-b-2 ${
                activeTab === 'users'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent hover:text-gray-600 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('users')}
            >
              Пользователи
            </button>
          </li>
          <li className="mr-2">
            <button
              className={`inline-block py-2 px-4 border-b-2 ${
                activeTab === 'books'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent hover:text-gray-600 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('books')}
            >
              Книги
            </button>
          </li>
          <li className="mr-2">
            <button
              className={`inline-block py-2 px-4 border-b-2 ${
                activeTab === 'categories'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent hover:text-gray-600 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('categories')}
            >
              Категории
            </button>
          </li>
          <li className="mr-2">
            <button
              className={`inline-block py-2 px-4 border-b-2 ${
                activeTab === 'authors'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent hover:text-gray-600 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('authors')}
            >
              Авторы
            </button>
          </li>
          <li className="mr-2">
            <button
              className={`inline-block py-2 px-4 border-b-2 ${
                activeTab === 'statistics'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent hover:text-gray-600 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('statistics')}
            >
              Статистика
            </button>
          </li>
        </ul>
      </div>

      {/* Содержимое табов */}
      <div className="bg-white shadow rounded-lg p-6">
        {activeTab === 'users' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Управление пользователями</h2>
            <p className="text-gray-600 mb-4">Здесь будет отображаться список зарегистрированных пользователей и инструменты для управления ими.</p>
            <div className="p-4 bg-gray-100 rounded-lg border">
              <p className="text-sm text-gray-500">Функциональность находится в разработке.</p>
            </div>
          </div>
        )}

        {activeTab === 'books' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Управление книгами</h2>
            <p className="text-gray-600 mb-4">Здесь будет отображаться список книг и инструменты для управления библиотекой.</p>
            <div className="p-4 bg-gray-100 rounded-lg border">
              <p className="text-sm text-gray-500">Функциональность находится в разработке.</p>
            </div>
          </div>
        )}

        {activeTab === 'categories' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Управление категориями</h2>
            <p className="text-gray-600 mb-4">Здесь будет отображаться список категорий и инструменты для их редактирования.</p>
            <div className="p-4 bg-gray-100 rounded-lg border">
              <p className="text-sm text-gray-500">Функциональность находится в разработке.</p>
            </div>
          </div>
        )}

        {activeTab === 'authors' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Управление авторами</h2>
            <p className="text-gray-600 mb-4">Здесь будет отображаться список авторов и инструменты для их редактирования.</p>
            <div className="p-4 bg-gray-100 rounded-lg border">
              <p className="text-sm text-gray-500">Функциональность находится в разработке.</p>
            </div>
          </div>
        )}

        {activeTab === 'statistics' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Статистика использования</h2>
            <p className="text-gray-600 mb-4">Здесь будет отображаться статистика использования сайта и библиотеки.</p>
            <div className="p-4 bg-gray-100 rounded-lg border">
              <p className="text-sm text-gray-500">Функциональность находится в разработке.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPage;
