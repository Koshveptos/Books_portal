import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApi } from '../contexts/ApiContext';
import { useNotification } from '../contexts/NotificationContext';
import { useAuth } from '../contexts/AuthContext';
import { Book } from '../types';
import { BookCard } from '../components/BookCard';
import { Rating } from '../components/Rating';
import { LikeButton } from '../components/LikeButton';
import { FavoriteButton } from '../components/FavoriteButton';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { AuthRequired } from '../components/AuthRequired';

export const BookDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const [book, setBook] = useState<Book | null>(null);
    const [similarBooks, setSimilarBooks] = useState<Book[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { api } = useApi();
    const { notify } = useNotification();
    const { isAuthenticated, isAdmin, isModerator } = useAuth();

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                setError(null);

                const [bookResponse, similarResponse] = await Promise.all([
                    api.get(`/books/${id}`),
                    api.get(`/books/${id}/similar`)
                ]);

                setBook(bookResponse.data);
                setSimilarBooks(similarResponse.data);
            } catch (err: any) {
                const errorMessage = err.response?.data?.detail || 'Ошибка при загрузке данных';
                setError(errorMessage);
                notify(errorMessage, 'error');
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, [api, id, notify]);

    const handleLike = async () => {
        try {
            await api.post(`/likes/${id}`);
            notify('Книга добавлена в понравившиеся', 'success');
            setBook(prev => prev ? { ...prev, is_liked: !prev.is_liked } : null);
        } catch (error) {
            notify('Ошибка при добавлении в понравившиеся', 'error');
        }
    };

    const handleFavorite = async () => {
        try {
            await api.post(`/favorites/${id}`);
            notify('Книга добавлена в избранное', 'success');
            setBook(prev => prev ? { ...prev, is_favorite: !prev.is_favorite } : null);
        } catch (error) {
            notify('Ошибка при добавлении в избранное', 'error');
        }
    };

    const handleRating = async (rating: number) => {
        try {
            await api.post('/ratings', { book_id: id, rating });
            notify('Оценка успешно сохранена', 'success');
            // Обновляем книгу после оценки
            const response = await api.get(`/books/${id}`);
            setBook(response.data);
        } catch (error) {
            notify('Ошибка при сохранении оценки', 'error');
        }
    };

    if (isLoading) {
        return <LoadingSpinner />;
    }

    if (error || !book) {
        return <ErrorMessage message={error || 'Книга не найдена'} />;
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Информация о книге */}
                <div className="md:col-span-2">
                    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
                        <div className="p-6">
                            <div className="flex justify-between items-start mb-4">
                                <h1 className="text-3xl font-bold text-gray-900">{book.title}</h1>
                                {(isAdmin || isModerator) && (
                                    <Link
                                        to={`/books/${book.id}/edit`}
                                        className="text-blue-600 hover:text-blue-800"
                                    >
                                        Редактировать
                                    </Link>
                                )}
                            </div>

                            <div className="flex items-center space-x-4 mb-4">
                                <Rating
                                    value={book.average_rating || 0}
                                    onChange={handleRating}
                                    disabled={!isAuthenticated}
                                />
                                <span className="text-gray-600">
                                    ({book.ratings_count || 0} оценок)
                                </span>
                            </div>

                            <div className="flex items-center space-x-4 mb-6">
                                {isAuthenticated ? (
                                    <>
                                        <LikeButton
                                            isLiked={book.is_liked || false}
                                            onClick={handleLike}
                                        />
                                        <FavoriteButton
                                            isFavorite={book.is_favorite || false}
                                            onClick={handleFavorite}
                                        />
                                    </>
                                ) : (
                                    <AuthRequired>
                                        <div className="flex items-center space-x-4">
                                            <LikeButton
                                                isLiked={false}
                                                onClick={() => {}}
                                                disabled
                                            />
                                            <FavoriteButton
                                                isFavorite={false}
                                                onClick={() => {}}
                                                disabled
                                            />
                                        </div>
                                    </AuthRequired>
                                )}
                            </div>

                            <div className="prose max-w-none mb-6">
                                <p className="text-gray-700">{book.description}</p>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Авторы</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {book.authors.map((author) => (
                                            <Link
                                                key={author.id}
                                                to={`/authors/${author.id}`}
                                                className="text-blue-600 hover:text-blue-800"
                                            >
                                                {author.name}
                                            </Link>
                                        ))}
                                    </div>
                                </div>

                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Категории</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {book.categories.map((category) => (
                                            <Link
                                                key={category.id}
                                                to={`/categories/${category.id}`}
                                                className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm hover:bg-green-200 transition-colors"
                                            >
                                                {category.name_categories}
                                            </Link>
                                        ))}
                                    </div>
                                </div>

                                {book.tags.length > 0 && (
                                    <div>
                                        <h3 className="text-lg font-semibold text-gray-900 mb-2">Теги</h3>
                                        <div className="flex flex-wrap gap-2">
                                            {book.tags.map((tag) => (
                                                <span
                                                    key={tag.id}
                                                    className="bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm"
                                                >
                                                    {tag.name}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Обложка книги */}
                <div className="md:col-span-1">
                    <div className="sticky top-8">
                        <img
                            src={book.cover_url || '/default-book-cover.jpg'}
                            alt={book.title}
                            className="w-full rounded-lg shadow-lg"
                        />
                    </div>
                </div>
            </div>

            {/* Похожие книги */}
            {similarBooks.length > 0 && (
                <section className="mt-12">
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">Похожие книги</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                        {similarBooks.map((similarBook) => (
                            <BookCard key={similarBook.id} book={similarBook} />
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
};
