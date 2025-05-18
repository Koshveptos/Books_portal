import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Tag } from '../types/tag';
import { Book } from '../types';
import api from '../services/api';
import { BookCard } from '../components/BookCard';

export const TagDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [tag, setTag] = useState<Tag | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTagData = async () => {
      try {
        const [tagResponse, booksResponse] = await Promise.all([
          api.get(`/tags/${id}`),
          api.get(`/tags/${id}/books`)
        ]);
        setTag(tagResponse.data);
        setBooks(booksResponse.data);
        setLoading(false);
      } catch (err) {
        setError('Ошибка при загрузке данных тега');
        setLoading(false);
      }
    };

    fetchTagData();
  }, [id]);

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </div>
    );
  }

  if (error || !tag) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error || 'Тег не найден'}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4">{tag.name_tag}</h1>
        <p className="text-gray-600">
          Количество книг: {books.length}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {books.map((book) => (
          <BookCard key={book.id} book={book} />
        ))}
      </div>

      {books.length === 0 && (
        <div className="text-center text-gray-500 mt-8">
          Нет книг с этим тегом
        </div>
      )}
    </div>
  );
};
