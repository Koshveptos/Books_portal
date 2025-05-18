import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Rating } from '../types';
import { ratingsService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const UserRatingsPage: React.FC = () => {
  const [ratings, setRatings] = useState<Rating[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    const fetchRatings = async () => {
      try {
        setLoading(true);
        const data = await ratingsService.getUserRatings();
        setRatings(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching ratings:', err);
        setError('Не удалось загрузить ваши оценки');
      } finally {
        setLoading(false);
      }
    };

    if (isAuthenticated) {
      fetchRatings();
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600">Пожалуйста, войдите в систему, чтобы просмотреть свои оценки.</p>
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

  if (ratings.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600">У вас пока нет оценок книг.</p>
        <Link to="/" className="text-blue-500 hover:text-blue-600 mt-4 inline-block">
          Перейти к книгам
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Мои оценки</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {ratings.map((rating) => (
          <div key={rating.id} className="bg-white shadow rounded-lg p-4">
            {rating.book && (
              <>
                <img
                  src={rating.book.cover}
                  alt={rating.book.title}
                  className="w-full h-48 object-cover rounded-lg mb-4"
                />
                <h2 className="text-xl font-semibold mb-2">{rating.book.title}</h2>
                <p className="text-gray-600 text-sm mb-2">
                  Авторы: {rating.book.authors.map(author => author.name).join(', ')}
                </p>
                <div className="mb-4">
                  <p className="text-gray-600 mb-2">Ваша оценка:</p>
                  <div className="flex items-center">
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((value) => (
                        <span
                          key={value}
                          className={`text-2xl ${
                            value <= rating.rating ? 'text-yellow-500' : 'text-gray-300'
                          }`}
                        >
                          ★
                        </span>
                      ))}
                    </div>
                    <span className="ml-2 text-gray-600">({rating.rating}/5)</span>
                  </div>
                </div>
                {rating.comment && (
                  <div className="mb-4">
                    <p className="text-gray-600 mb-2">Ваш комментарий:</p>
                    <p className="text-gray-800">{rating.comment}</p>
                  </div>
                )}
                <div className="flex justify-end">
                  <Link
                    to={`/books/${rating.book.id}`}
                    className="text-blue-500 hover:text-blue-600"
                  >
                    Подробнее о книге
                  </Link>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default UserRatingsPage;
