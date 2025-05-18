import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { categoryService, bookService } from '../services/api';
import { Category, Book } from '../types';
import { useAuth } from '../contexts/AuthContext';

const CategoryPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [category, setCategory] = useState<Category | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, hasRole } = useAuth();

  useEffect(() => {
    const fetchCategoryData = async () => {
      try {
        setLoading(true);
        const categoryData = await categoryService.getCategory(Number(id));
        setCategory(categoryData);

        const booksData = await bookService.getBooksByCategory(Number(id));
        setBooks(booksData.books || []);
      } catch (err) {
        setError('Ошибка при загрузке данных категории');
        console.error('Error fetching category data:', err);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchCategoryData();
    }
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !category) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-red-500 text-xl">{error || 'Категория не найдена'}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
        <h1 className="text-3xl font-bold mb-4">{category.name_categories}</h1>
        {category.description && (
          <div className="prose max-w-none mb-6">
            <p className="text-gray-700">{category.description}</p>
          </div>
        )}
      </div>

      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Книги в категории</h2>
        {(hasRole('admin') || hasRole('moderator')) && (
          <Link
            to="/books/add"
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Добавить книгу
          </Link>
        )}
      </div>

      {books.length === 0 ? (
        <p className="text-gray-500">В этой категории пока нет книг</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {books.map((book) => (
            <div key={book.id} className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-xl font-semibold mb-2">{book.title}</h3>
              <p className="text-gray-600 text-sm mb-2">
                Авторы: {book.authors.map(author => author.name).join(', ') || 'Неизвестен'}
              </p>
              {book.description && (
                <p className="text-gray-700 text-sm line-clamp-3">
                  {book.description}
                </p>
              )}
              <div className="flex justify-between items-center mt-4">
                <Link
                  to={`/books/${book.id}`}
                  className="text-blue-500 hover:text-blue-600"
                >
                  Подробнее
                </Link>
                {(hasRole('admin') || hasRole('moderator')) && (
                  <div className="space-x-2">
                    <Link
                      to={`/books/${book.id}/edit`}
                      className="text-yellow-500 hover:text-yellow-600"
                    >
                      Редактировать
                    </Link>
                    <button
                      onClick={() => {
                        if (window.confirm('Вы уверены, что хотите удалить эту книгу?')) {
                          bookService.deleteBook(book.id);
                        }
                      }}
                      className="text-red-500 hover:text-red-600"
                    >
                      Удалить
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CategoryPage;
