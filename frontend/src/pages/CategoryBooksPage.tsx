import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Book } from '../types';
import api from '../services/api';
import { BookList } from '../components/BookList';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

export const CategoryBooksPage: React.FC = () => {
    const { categoryId } = useParams<{ categoryId: string }>();
    const [books, setBooks] = useState<Book[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchBooks = async () => {
            try {
                setLoading(true);
                const response = await api.get<Book[]>(`/books/category/${categoryId}`);
                setBooks(response.data);
                setError(null);
            } catch (err) {
                setError('Ошибка при загрузке книг категории');
                console.error('Error fetching category books:', err);
            } finally {
                setLoading(false);
            }
        };

        if (categoryId) {
            fetchBooks();
        }
    }, [categoryId]);

    if (loading) {
        return <LoadingSpinner />;
    }

    if (error) {
        return <ErrorMessage message={error} />;
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mb-8">Книги категории</h1>
            {books.length > 0 ? (
                <BookList books={books} />
            ) : (
                <p className="text-gray-500 text-center">В этой категории пока нет книг</p>
            )}
        </div>
    );
};
