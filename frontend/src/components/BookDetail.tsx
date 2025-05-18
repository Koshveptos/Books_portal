import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Book, Rating } from '../types';
import { bookService, favoritesService, likesService, ratingsService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface BookDetailProps {
  book: Book;
  onUpdate?: () => void;
}

export const BookDetail: React.FC<BookDetailProps> = ({ book, onUpdate }) => {
  const { id } = useParams<{ id: string }>();
  const [userRating, setUserRating] = useState<number>(0);
  const [comment, setComment] = useState('');
  const [showRatingModal, setShowRatingModal] = useState(false);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    const fetchUserRating = async () => {
      if (!isAuthenticated) return;
      try {
        const ratings = await ratingsService.getUserRatings();
        const bookRating = ratings.find(r => r.book_id === book.id);
        if (bookRating) {
          setUserRating(bookRating.rating);
          setComment(bookRating.comment || '');
        }
      } catch (err) {
        console.error('Error fetching user interactions:', err);
      }
    };

    fetchUserRating();
  }, [book.id, isAuthenticated]);

  const handleRatingSubmit = async () => {
    if (!isAuthenticated || !userRating) return;

    try {
      await ratingsService.rateBook(book.id, userRating, comment);
      alert('Ваша оценка сохранена');
      setShowRatingModal(false);
      onUpdate?.();
    } catch (err) {
      console.error('Error rating book:', err);
      alert('Ошибка при сохранении оценки');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <img
            src={book.cover}
            alt={book.title}
            className="w-full h-auto rounded-lg shadow-md"
          />
        </div>
        <div>
          <h1 className="text-3xl font-bold mb-4">{book.title}</h1>
          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-semibold mb-2">Авторы</h2>
              <p className="text-gray-600">
                {book.authors.map(author => author.name).join(', ')}
              </p>
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Категории</h2>
              <div className="flex flex-wrap gap-2">
                {book.categories.map(category => (
                  <span
                    key={category.id}
                    className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
                  >
                    {category.name_categories}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Описание</h2>
              <p className="text-gray-600">{book.description}</p>
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Детали</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-gray-600">Год издания:</p>
                  <p className="font-semibold">{book.year}</p>
                </div>
                <div>
                  <p className="text-gray-600">ISBN:</p>
                  <p className="font-semibold">{book.isbn}</p>
                </div>
                <div>
                  <p className="text-gray-600">Издатель:</p>
                  <p className="font-semibold">{book.publisher}</p>
                </div>
                <div>
                  <p className="text-gray-600">Язык:</p>
                  <p className="font-semibold">{book.language}</p>
                </div>
                <div>
                  <p className="text-gray-600">Средний рейтинг:</p>
                  <p className="font-semibold">{book.average_rating?.toFixed(1) || 'Нет оценок'}</p>
                </div>
                <div>
                  <p className="text-gray-600">Количество оценок:</p>
                  <p className="font-semibold">{book.ratings_count || 0}</p>
                </div>
              </div>
            </div>
          </div>
          {isAuthenticated && (
            <button
              onClick={() => setShowRatingModal(true)}
              className="mt-6 bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
            >
              Оценить книгу
            </button>
          )}
        </div>
      </div>

      {showRatingModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-lg w-96">
            <h3 className="text-xl font-semibold mb-4">Оценить книгу</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Оценка
              </label>
              <div className="flex space-x-2">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    key={value}
                    onClick={() => setUserRating(value)}
                    className={`w-10 h-10 rounded-full ${
                      userRating === value
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    {value}
                  </button>
                ))}
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Комментарий
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="w-full border border-gray-300 rounded-md p-2"
                rows={3}
                placeholder="Ваш отзыв о книге..."
              />
            </div>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowRatingModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Отмена
              </button>
              <button
                onClick={handleRatingSubmit}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Сохранить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BookDetail;
