import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Category, Book } from '../types';
import api from '../services/api';

const CategoryDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [category, setCategory] = useState<Category | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { hasRole } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchCategory = async () => {
      try {
        const [categoryResponse, booksResponse] = await Promise.all([
          api.get(`/categories/${id}`),
          api.get(`/categories/${id}/books`)
        ]);
        setCategory(categoryResponse.data);
        setBooks(booksResponse.data);
        setLoading(false);
      } catch (err) {
        setError('Ошибка при загрузке информации о категории');
        setLoading(false);
      }
    };

    fetchCategory();
  }, [id]);

  const handleDelete = async () => {
    if (!window.confirm('Вы уверены, что хотите удалить эту категорию?')) {
      return;
    }

    try {
      await api.delete(`/categories/${id}`);
      navigate('/categories');
    } catch (err) {
      setError('Ошибка при удалении категории');
    }
  };

  const handleEdit = () => {
    navigate(`/categories/${id}/edit`);
  };

  if (loading) {
    return <div className="flex justify-center items-center h-screen">Загрузка...</div>;
  }

  if (error || !category) {
    return <div className="text-red-500 text-center p-4">{error || 'Категория не найдена'}</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex flex-col md:flex-row gap-8">
          <div className="md:w-1/3">
            <img
              src={category.image}
              alt={category.name_categories}
              className="w-full h-auto rounded-lg shadow-lg"
            />
          </div>
          <div className="md:w-2/3">
            <h1 className="text-3xl font-bold mb-4">{category.name_categories}</h1>

            <div className="mb-4">
              <h2 className="text-xl font-semibold mb-2">Описание:</h2>
              <p className="text-gray-700">{category.description}</p>
            </div>

            <div className="mt-6 flex space-x-4">
              <Link
                to={`/categories/${id}/books`}
                className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              >
                Посмотреть книги
              </Link>

              {(hasRole('admin') || hasRole('moderator')) && (
                <>
                  <button
                    className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                    onClick={handleEdit}
                  >
                    Редактировать
                  </button>
                  <button
                    className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
                    onClick={handleDelete}
                  >
                    Удалить
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">Книги в категории</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {books.map((book) => (
              <div key={book.id} className="bg-gray-50 rounded-lg p-4">
                <img
                  src={book.cover}
                  alt={book.title}
                  className="w-full h-48 object-cover rounded-lg mb-4"
                />
                <h3 className="text-lg font-semibold mb-2">{book.title}</h3>
                <p className="text-gray-600 text-sm mb-2">
                  Авторы: {book.authors.map(a => a.name).join(', ')}
                </p>
                <p className="text-gray-600 text-sm mb-2">Год: {book.year}</p>
                <div className="flex flex-wrap gap-2">
                  {book.tags.map((tag) => (
                    <span key={tag.id} className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded-full">
                      {tag.name}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CategoryDetailPage;
