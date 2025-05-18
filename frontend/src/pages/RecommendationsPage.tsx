import React, { useEffect, useState } from 'react';
import { useApi } from '../contexts/ApiContext';
import { useNotification } from '../contexts/NotificationContext';
import { useAuth } from '../contexts/AuthContext';
import { Book } from '../types';
import { BookCard } from '../components/BookCard';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { AuthRequired } from '../components/AuthRequired';
import { Tabs } from '../components/Tabs';

type RecommendationType = 'hybrid' | 'collaborative' | 'content' | 'popularity' | 'author' | 'category' | 'tag';

export const RecommendationsPage: React.FC = () => {
    const [books, setBooks] = useState<Book[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<RecommendationType>('hybrid');
    const { api } = useApi();
    const { notify } = useNotification();
    const { isAuthenticated } = useAuth();

    useEffect(() => {
        const fetchRecommendations = async () => {
            try {
                setIsLoading(true);
                setError(null);

                const response = await api.get('/recommendations', {
                    params: {
                        recommendation_type: activeTab,
                        limit: 12
                    }
                });

                setBooks(response.data);
            } catch (err: any) {
                const errorMessage = err.response?.data?.detail || 'Ошибка при загрузке рекомендаций';
                setError(errorMessage);
                notify(errorMessage, 'error');
            } finally {
                setIsLoading(false);
            }
        };

        if (isAuthenticated) {
            fetchRecommendations();
        }
    }, [api, activeTab, isAuthenticated, notify]);

    if (!isAuthenticated) {
        return (
            <AuthRequired>
                <div className="container mx-auto px-4 py-8">
                    <h1 className="text-2xl font-bold text-gray-900 mb-4">
                        Персональные рекомендации
                    </h1>
                    <p className="text-gray-600">
                        Войдите в систему, чтобы получить персональные рекомендации книг
                    </p>
                </div>
            </AuthRequired>
        );
    }

    if (isLoading) {
        return <LoadingSpinner />;
    }

    if (error) {
        return <ErrorMessage message={error} />;
    }

    const tabs = [
        {
            id: 'hybrid',
            label: 'Все рекомендации',
            content: null
        },
        {
            id: 'collaborative',
            label: 'На основе оценок',
            content: null
        },
        {
            id: 'content',
            label: 'По интересам',
            content: null
        },
        {
            id: 'popularity',
            label: 'Популярные',
            content: null
        },
        {
            id: 'author',
            label: 'Любимые авторы',
            content: null
        },
        {
            id: 'category',
            label: 'Любимые категории',
            content: null
        },
        {
            id: 'tag',
            label: 'По тегам',
            content: null
        }
    ];

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-6">
                Персональные рекомендации
            </h1>

            <Tabs
                tabs={tabs}
                defaultTab={activeTab}
                onChange={(tab) => setActiveTab(tab as RecommendationType)}
            />

            {books.length === 0 ? (
                <div className="text-center py-8">
                    <p className="text-gray-600">
                        Нет рекомендаций для отображения. Попробуйте оценить больше книг или изменить тип рекомендаций.
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                    {books.map((book) => (
                        <BookCard key={book.id} book={book} />
                    ))}
                </div>
            )}
        </div>
    );
};
