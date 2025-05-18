import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Author } from '../types';
import api from '../services/api';

const AuthorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [author, setAuthor] = useState<Author | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { hasRole } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAuthor = async () => {
      try {
        const response = await api.get(`/authors/${id}`);
        setAuthor(response.data);
        setLoading(false);
      } catch (err) {
        setError('Ошибка при загрузке автора');
        setLoading(false);
      }
    };

    fetchAuthor();
  }, [id]);

  const handleDelete = async () => {
    if (!window.confirm('Вы уверены, что хотите удалить этого автора?')) {
      return;
    }

    try {
      await api.delete(`/authors/${id}`);
      navigate('/authors');
    } catch (err) {
      setError('Ошибка при удалении автора');
    }
  };

  const handleEdit = () => {
    navigate(`/authors/${id}/edit`);
  };

  if (loading) {
    return <div className="flex justify-center items-center h-screen">Загрузка...</div>;
  }

  if (error || !author) {
    return <div className="text-red-500 text-center p-4">{error || 'Автор не найден'}</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex flex-col md:flex-row gap-8">
          <div className="md:w-1/3">
            <img
              src={author.photo}
              alt={author.name}
              className="w-full h-auto rounded-lg shadow-lg"
            />
          </div>
          <div className="md:w-2/3">
            <h1 className="text-3xl font-bold mb-4">{author.name}</h1>

            <div className="mb-4">
              <h2 className="text-xl font-semibold mb-2">Биография:</h2>
              <p className="text-gray-700">{author.biography}</p>
            </div>

            <div className="mb-4">
              <h2 className="text-xl font-semibold mb-2">Информация:</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-gray-600">Дата рождения:</p>
                  <p className="font-semibold">{author.birth_date}</p>
                </div>
                {author.death_date && (
                  <div>
                    <p className="text-gray-600">Дата смерти:</p>
                    <p className="font-semibold">{author.death_date}</p>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-6 flex space-x-4">
              <Link
                to={`/authors/${id}/books`}
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
      </div>
    </div>
  );
};

export default AuthorDetailPage;
