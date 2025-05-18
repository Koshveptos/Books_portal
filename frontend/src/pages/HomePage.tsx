import React, { useEffect, useState } from 'react';
import { useApi } from '../contexts/ApiContext';
import { useNotification } from '../contexts/NotificationContext';
import { Book, Category } from '../types';
import { BookCard } from '../components/BookCard';
import { Card } from '../components/Card';
import { Link } from 'react-router-dom';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

export const HomePage: React.FC = () => {
    const [recentBooks, setRecentBooks] = useState<Book[]>([]);
    const [categories, setCategories] = useState<Category[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { api } = useApi();
    const { notify } = useNotification();

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                setError(null);

                const [booksResponse, categoriesResponse] = await Promise.all([
                    api.get('/books', { params: { sort: 'new', limit: 8 } }),
                    api.get('/categories', { params: { limit: 6 } })
                ]);

                setRecentBooks(booksResponse.data);
                setCategories(categoriesResponse.data);
            } catch (err: any) {
                const errorMessage = err.response?.data?.detail || 'Ошибка при загрузке данных';
                setError(errorMessage);
                notify(errorMessage, 'error');
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, [api, notify]);

    if (isLoading) {
        return <LoadingSpinner />;
    }

    if (error) {
        return <ErrorMessage message={error} />;
    }

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Недавно добавленные книги */}
            <section className="mb-12">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">Недавно добавленные книги</h2>
                    <Link
                        to="/books"
                        className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                        Все книги →
                    </Link>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                    {recentBooks.map((book) => (
                        <BookCard key={book.id} book={book} />
                    ))}
                </div>
            </section>

            {/* Категории */}
            <section>
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">Категории</h2>
                    <Link
                        to="/categories"
                        className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                        Все категории →
                    </Link>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                    {categories.map((category) => (
                        <Link key={category.id} to={`/categories/${category.id}`}>
                            <Card className="h-full hover:shadow-lg transition-shadow duration-300">
                                <div className="p-6">
                                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                                        {category.name_categories}
                                    </h3>
                                    {category.description && (
                                        <p className="text-gray-600 line-clamp-2">
                                            {category.description}
                                        </p>
                                    )}
                                </div>
                            </Card>
                        </Link>
                    ))}
                </div>
            </section>
        </div>
    );
};
