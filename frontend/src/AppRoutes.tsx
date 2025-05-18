import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';

// Страницы
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { BookDetailPage } from './pages/BookDetailPage';
import AuthorDetailPage from './pages/AuthorDetailPage';
import CategoryDetailPage from './pages/CategoryDetailPage';
import { TagDetailPage } from './pages/TagDetailPage';
import { SearchPage } from './pages/SearchPage';
import ProfilePage from './pages/ProfilePage';
import NotFoundPage from './pages/NotFoundPage';
import { BooksPage } from './pages/BooksPage';
import { AuthorsPage } from './pages/AuthorsPage';
import { CategoriesPage } from './pages/CategoriesPage';
import { TagsPage } from './pages/TagsPage';
import UserFavoritesPage from './pages/UserFavoritesPage';
import UserRatingsPage from './pages/UserRatingsPage';
import AdminPage from './pages/AdminPage';

// Компоненты
import { AuthRequired } from './components/AuthRequired';

export const AppRoutes: React.FC = () => {
  const { isAuthenticated, isAdmin, isModerator } = useAuth();

  return (
    <Routes>
      {/* Публичные маршруты */}
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/books" element={<BooksPage />} />
      <Route path="/books/:id" element={<BookDetailPage />} />
      <Route path="/authors" element={<AuthorsPage />} />
      <Route path="/authors/:id" element={<AuthorDetailPage />} />
      <Route path="/categories" element={<CategoriesPage />} />
      <Route path="/categories/:id" element={<CategoryDetailPage />} />
      <Route path="/tags" element={<TagsPage />} />
      <Route path="/tags/:id" element={<TagDetailPage />} />
      <Route path="/search" element={<SearchPage />} />

      {/* Защищенные маршруты */}
      <Route
        path="/profile"
        element={
          <AuthRequired>
            <ProfilePage />
          </AuthRequired>
        }
      />
      <Route
        path="/favorites"
        element={
          <AuthRequired>
            <UserFavoritesPage />
          </AuthRequired>
        }
      />
      <Route
        path="/ratings"
        element={
          <AuthRequired>
            <UserRatingsPage />
          </AuthRequired>
        }
      />

      {/* Административные маршруты */}
      {(isAdmin || isModerator) && (
        <Route
          path="/admin/*"
          element={
            <AuthRequired requiredRole={isAdmin ? 'admin' : 'moderator'}>
              <AdminPage />
            </AuthRequired>
          }
        />
      )}

      {/* Обработка несуществующих маршрутов */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};
