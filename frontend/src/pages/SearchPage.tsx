import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApi } from '../contexts/ApiContext';
import { useNotification } from '../contexts/NotificationContext';
import { Book } from '../types';
import { BookCard } from '../components/BookCard';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import EmptyState from '../components/EmptyState';
import { Pagination } from '../components/Pagination';

export const SearchPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const query = searchParams.get('q') || '';
    const page = parseInt(searchParams.get('page') || '1');
    const [books, setBooks] = useState<Book[]>([]);
    const [totalPages, setTotalPages] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { api } = useApi();
    const { notify } = useNotification();

    useEffect(() => {
        const fetchBooks = async () => {
            if (!query) {
                setBooks([]);
                setIsLoading(false);
                return;
            }

            try {
                setIsLoading(true);
                setError(null);

                const response = await api.get('/search', {
                    params: {
                        q: query,
                        page,
                        limit: 12
                    }
                });

                setBooks(response.data.items);
                setTotalPages(Math.ceil(response.data.total / 12));
            } catch (err: any) {
                const errorMessage = err.response?.data?.detail || 'Ошибка при поиске книг';
                setError(errorMessage);
                notify(errorMessage, 'error');
            } finally {
                setIsLoading(false);
            }
        };

        fetchBooks();
    }, [api, query, page, notify]);

    if (isLoading) {
        return <LoadingSpinner />;
    }

    if (error) {
        return <ErrorMessage message={error} />;
    }

    if (!query) {
        return (
            <EmptyState
                title="Поиск книг"
                description="Введите поисковый запрос, чтобы найти интересующие вас книги"
            />
        );
    }

    if (books.length === 0) {
        return (
            <EmptyState
                title="Ничего не найдено"
                description={`По запросу "${query}" ничего не найдено. Попробуйте изменить параметры поиска.`}
            />
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                    Результаты поиска: {query}
                </h1>
                <p className="text-gray-600">
                    Найдено книг: {books.length}
                </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {books.map((book) => (
                    <BookCard key={book.id} book={book} />
                ))}
            </div>

            {totalPages > 1 && (
                <div className="mt-8">
                    <Pagination
                        currentPage={page}
                        totalPages={totalPages}
                        onPageChange={(newPage) => {
                            const params = new URLSearchParams(searchParams);
                            params.set('page', newPage.toString());
                            window.history.pushState({}, '', `?${params.toString()}`);
                        }}
                    />
                </div>
            )}
        </div>
    );
};
