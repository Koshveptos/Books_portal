import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { HomePage } from '../pages/HomePage';
import { BookDetailPage } from '../pages/BookDetailPage';
import AuthorPage from '../pages/AuthorPage';
import CategoryPage from '../pages/CategoryPage';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import ProfilePage from '../pages/ProfilePage';
import AddBookPage from '../pages/AddBookPage';
import AddAuthorPage from '../pages/AddAuthorPage';
import AddCategoryPage from '../pages/AddCategoryPage';
import EditBookPage from '../pages/EditBookPage';
import EditAuthorPage from '../pages/EditAuthorPage';
import EditCategoryPage from '../pages/EditCategoryPage';
import { SearchPage } from '../pages/SearchPage';
import UserBooksPage from '../pages/UserBooksPage';
import UserFavoritesPage from '../pages/UserFavoritesPage';
import UserRatingsPage from '../pages/UserRatingsPage';
import NotFoundPage from '../pages/NotFoundPage';
import { AuthRequired } from '../components/AuthRequired';
import { AdminRoute } from '../components/AdminRoute';
import { AuthorBooksPage } from '../pages/AuthorBooksPage';
import { CategoryBooksPage } from '../pages/CategoryBooksPage';
import { BooksPage } from '../pages/BooksPage';

const AppRoutes: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/books" element={<BooksPage />} />
          <Route path="/books/:id" element={<BookDetailPage />} />
          <Route path="/authors" element={<AuthorPage />} />
          <Route path="/authors/:authorId/books" element={<AuthorBooksPage />} />
          <Route path="/categories" element={<CategoryPage />} />
          <Route path="/categories/:categoryId/books" element={<CategoryBooksPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route path="/profile" element={
            <AuthRequired>
              <ProfilePage />
            </AuthRequired>
          } />

          <Route path="/my-books" element={
            <AuthRequired>
              <UserBooksPage />
            </AuthRequired>
          } />

          <Route path="/favorites" element={
            <AuthRequired>
              <UserFavoritesPage />
            </AuthRequired>
          } />

          <Route path="/ratings" element={
            <AuthRequired>
              <UserRatingsPage />
            </AuthRequired>
          } />

          <Route path="/add-book" element={
            <AdminRoute>
              <AddBookPage />
            </AdminRoute>
          } />

          <Route path="/add-author" element={
            <AdminRoute>
              <AddAuthorPage />
            </AdminRoute>
          } />

          <Route path="/add-category" element={
            <AdminRoute>
              <AddCategoryPage />
            </AdminRoute>
          } />

          <Route path="/edit-book/:id" element={
            <AdminRoute>
              <EditBookPage />
            </AdminRoute>
          } />

          <Route path="/edit-author/:id" element={
            <AdminRoute>
              <EditAuthorPage />
            </AdminRoute>
          } />

          <Route path="/edit-category/:id" element={
            <AdminRoute>
              <EditCategoryPage />
            </AdminRoute>
          } />

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
};

export default AppRoutes;
