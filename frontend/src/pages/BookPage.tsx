import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { bookService } from '../services/book';
import { useAuth } from '../contexts/AuthContext';
import { Spinner } from '../components/Spinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { Book } from '../types/book';

export const BookPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { isAuthenticated, hasRole } = useAuth();
    const [book, setBook] = useState<Book | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchBook = async () => {
            try {
                if (!id) return;
                const data = await bookService.getBook(parseInt(id));
                setBook(data);
            } catch (err) {
                setError('Ошибка при загрузке книги');
            } finally {
                setLoading(false);
            }
        };

        fetchBook();
    }, [id]);

    const handleDelete = async () => {
        if (!id || !window.confirm('Вы уверены, что хотите удалить эту книгу?')) return;

        try {
            await bookService.deleteBook(parseInt(id));
            navigate('/books');
        } catch (err) {
            setError('Ошибка при удалении книги');
        }
    };

    if (loading) return <Spinner />;
    if (error) return <ErrorMessage message={error} />;
    if (!book) return <ErrorMessage message="Книга не найдена" />;

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="md:flex">
                    <div className="md:flex-shrink-0">
                        <img
                            className="h-48 w-full object-cover md:w-48"
                            src={book.cover_image || '/placeholder.png'}
                            alt={book.title}
                        />
                    </div>
                    <div className="p-8">
                        <div className="uppercase tracking-wide text-sm text-indigo-500 font-semibold">
                            {book.category?.name}
                        </div>
                        <h1 className="mt-2 text-3xl font-bold text-gray-900">
                            {book.title}
                        </h1>
                        <p className="mt-2 text-gray-600">
                            Автор: {book.author?.name}
                        </p>
                        <p className="mt-2 text-gray-600">
                            Год издания: {book.publication_year}
                        </p>
                        <p className="mt-2 text-gray-600">
                            ISBN: {book.isbn}
                        </p>
                        <div className="mt-4">
                            <h2 className="text-xl font-semibold text-gray-900">Описание</h2>
                            <p className="mt-2 text-gray-600">{book.description}</p>
                        </div>
                        {(hasRole('admin') || hasRole('moderator')) && (
                            <div className="mt-6 flex space-x-4">
                                <button
                                    onClick={() => navigate(`/books/${id}/edit`)}
                                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                                >
                                    Редактировать
                                </button>
                                {hasRole('admin') && (
                                    <button
                                        onClick={handleDelete}
                                        className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                                    >
                                        Удалить
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
