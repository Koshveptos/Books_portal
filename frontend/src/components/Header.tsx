import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { SearchBar } from './SearchBar';

const Header: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen);
  };

  return (
    <header className="bg-blue-700 text-white shadow-md">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Link to="/" className="text-2xl font-bold">BooksPortal</Link>
            <nav className="ml-8 hidden md:block">
              <ul className="flex space-x-6">
                <li>
                  <Link to="/" className="hover:text-blue-200 transition-colors">Главная</Link>
                </li>
                <li>
                  <Link to="/books" className="hover:text-blue-200 transition-colors">Книги</Link>
                </li>
                <li>
                  <Link to="/categories" className="hover:text-blue-200 transition-colors">Категории</Link>
                </li>
                <li>
                  <Link to="/authors" className="hover:text-blue-200 transition-colors">Авторы</Link>
                </li>
                <li>
                  <Link to="/tags" className="hover:text-blue-200 transition-colors">Теги</Link>
                </li>
              </ul>
            </nav>
          </div>

          {/* Мобильное меню для маленьких экранов */}
          <div className="md:hidden">
            <button onClick={toggleMobileMenu} className="p-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>

          <div className="hidden md:flex items-center space-x-4">
            <div className="flex-1">
              <SearchBar className="w-full" />
            </div>

            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <Link to="/profile" className="hover:text-blue-200 transition-colors">
                  {user?.email}
                </Link>
                <button
                  onClick={handleLogout}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm transition-colors"
                >
                  Выйти
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  to="/login"
                  className="bg-transparent hover:bg-blue-600 text-white px-4 py-2 border border-white rounded-md text-sm transition-colors"
                >
                  Войти
                </Link>
                <Link
                  to="/register"
                  className="bg-white text-blue-700 hover:bg-gray-100 px-4 py-2 rounded-md text-sm transition-colors"
                >
                  Регистрация
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Мобильное меню */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-blue-800 py-4">
          <nav className="container mx-auto px-4">
            <ul className="space-y-3">
              <li>
                <Link to="/" className="block hover:text-blue-200 transition-colors" onClick={() => setMobileMenuOpen(false)}>
                  Главная
                </Link>
              </li>
              <li>
                <Link to="/books" className="block hover:text-blue-200 transition-colors" onClick={() => setMobileMenuOpen(false)}>
                  Книги
                </Link>
              </li>
              <li>
                <Link to="/categories" className="block hover:text-blue-200 transition-colors" onClick={() => setMobileMenuOpen(false)}>
                  Категории
                </Link>
              </li>
              <li>
                <Link to="/authors" className="block hover:text-blue-200 transition-colors" onClick={() => setMobileMenuOpen(false)}>
                  Авторы
                </Link>
              </li>
              <li>
                <Link to="/tags" className="block hover:text-blue-200 transition-colors" onClick={() => setMobileMenuOpen(false)}>
                  Теги
                </Link>
              </li>
            </ul>

            <div className="mt-4">
              <SearchBar className="w-full" />
            </div>

            <div className="mt-4 space-y-3">
              {isAuthenticated ? (
                <>
                  <Link to="/profile" className="block hover:text-blue-200 transition-colors" onClick={() => setMobileMenuOpen(false)}>
                    Мой профиль
                  </Link>
                  <button
                    onClick={() => {
                      handleLogout();
                      setMobileMenuOpen(false);
                    }}
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm transition-colors w-full"
                  >
                    Выйти
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="bg-transparent hover:bg-blue-600 text-white px-4 py-2 border border-white rounded-md text-sm transition-colors text-center block"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Войти
                  </Link>
                  <Link
                    to="/register"
                    className="bg-white text-blue-700 hover:bg-gray-100 px-4 py-2 rounded-md text-sm transition-colors text-center block"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Регистрация
                  </Link>
                </>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
};

export default Header;
