import React from 'react';
import { Link } from 'react-router-dom';

export const UnauthorizedPage: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md text-center">
        <h1 className="text-2xl font-bold text-red-600 mb-4">Доступ запрещен</h1>
        <p className="text-gray-700 mb-6">
          У вас недостаточно прав для доступа к этой странице.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            to="/"
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            На главную
          </Link>
          <Link
            to="/login"
            className="px-4 py-2 border border-blue-600 text-blue-600 rounded hover:bg-blue-50 transition-colors"
          >
            Войти под другим аккаунтом
          </Link>
        </div>
      </div>
    </div>
  );
};

export default UnauthorizedPage;
