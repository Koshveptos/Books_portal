import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Book } from '../types';
import { bookService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const UserBooksPage: React.FC = () => {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setLoading(true);
        const data = await bookService.getBooks();
        setBooks(data.books || []);
        setError(null);
      } catch (err) {
        console.error('Error fetching books:', err);
        setError('Не удалось загрузить книги');
      } finally {
        setLoading(false);
      }
    };

    if (isAuthenticated) {
      fetchBooks();
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600">Пожалуйста, войдите в систему, чтобы просмотреть свои книги.</p>
        <Link to="/login" className="text-blue-500 hover:text-blue-600 mt-4 inline-block">
          Войти
        </Link>
      </div>
    );
  }

  if (loading) {
    return <div className="text-center py-8">Загрузка...</div>;
  }

  if (error) {
    return <div className="text-red-500 text-center py-8">{error}</div>;
  }

  if (books.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600">У вас пока нет книг.</p>
        <Link to="/" className="text-blue-500 hover:text-blue-600 mt-4 inline-block">
          Перейти к книгам
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Мои книги</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {books.map((book) => (
          <div key={book.id} className="bg-white shadow rounded-lg p-4">
            <img
              src={book.cover}
              alt={book.title}
              className="w-full h-48 object-cover rounded-lg mb-4"
            />
            <h2 className="text-xl font-semibold mb-2">{book.title}</h2>
            <p className="text-gray-600 text-sm mb-2">
              Авторы: {book.authors.map(author => author.name).join(', ')}
            </p>
            <p className="text-gray-600 text-sm mb-2">Год: {book.year}</p>
            <div className="flex flex-wrap gap-2 mb-4">
              {book.categories.map((category) => (
                <span key={category.id} className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                  {category.name_categories}
                </span>
              ))}
            </div>
            <div className="flex justify-end">
              <Link
                to={`/books/${book.id}`}
                className="text-blue-500 hover:text-blue-600"
              >
                Подробнее
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default UserBooksPage;
