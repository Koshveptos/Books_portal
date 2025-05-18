import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useApi } from '../contexts/ApiContext';
import { useNotification } from '../contexts/NotificationContext';
import { Book } from '../types';
import { Card } from './Card';
import { LikeButton } from './LikeButton';
import { FavoriteButton } from './FavoriteButton';
import { Rating } from './Rating';
import { AuthRequired } from './AuthRequired';

interface BookCardProps {
    book: Book;
    onUpdate?: () => void;
}

export const BookCard: React.FC<BookCardProps> = ({ book, onUpdate }) => {
    const { isAuthenticated } = useAuth();
    const { api } = useApi();
    const { notify } = useNotification();

    const handleLike = async () => {
        try {
            await api.post(`/likes/${book.id}`);
            notify('Книга добавлена в понравившиеся', 'success');
            onUpdate?.();
        } catch (error) {
            notify('Ошибка при добавлении в понравившиеся', 'error');
        }
    };

    const handleFavorite = async () => {
        try {
            await api.post(`/favorites/${book.id}`);
            notify('Книга добавлена в избранное', 'success');
            onUpdate?.();
        } catch (error) {
            notify('Ошибка при добавлении в избранное', 'error');
        }
    };

    const handleRating = async (rating: number) => {
        try {
            await api.post(`/ratings`, { book_id: book.id, rating });
            notify('Оценка успешно сохранена', 'success');
            onUpdate?.();
        } catch (error) {
            notify('Ошибка при сохранении оценки', 'error');
        }
    };

    return (
        <Card className="relative group hover:shadow-lg transition-shadow duration-300">
            <Link to={`/books/${book.id}`} className="block">
                <div className="aspect-w-2 aspect-h-3">
                    <img
                        src={book.cover_url || '/default-book-cover.jpg'}
                        alt={book.title}
                        className="object-cover w-full h-full rounded-t-lg"
                    />
                </div>
                <div className="p-4">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{book.title}</h3>
                    <p className="text-sm text-gray-600 mb-2">
                        {book.authors?.map(author => author.name).join(', ')}
                    </p>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <Rating
                                value={book.average_rating || 0}
                                onChange={handleRating}
                                disabled={!isAuthenticated}
                            />
                            <span className="text-sm text-gray-500">
                                ({book.ratings_count || 0})
                            </span>
                        </div>
                        <div className="flex items-center space-x-2">
                            {isAuthenticated ? (
                                <>
                                    <LikeButton
                                        isLiked={book.is_liked || false}
                                        onClick={handleLike}
                                        className="text-gray-500 hover:text-red-500"
                                    />
                                    <FavoriteButton
                                        isFavorite={book.is_favorite || false}
                                        onClick={handleFavorite}
                                        className="text-gray-500 hover:text-yellow-500"
                                    />
                                </>
                            ) : (
                                <AuthRequired>
                                    <div className="flex items-center space-x-2">
                                        <LikeButton
                                            isLiked={false}
                                            onClick={() => {}}
                                            disabled
                                            className="text-gray-300"
                                        />
                                        <FavoriteButton
                                            isFavorite={false}
                                            onClick={() => {}}
                                            disabled
                                            className="text-gray-300"
                                        />
                                    </div>
                                </AuthRequired>
                            )}
                        </div>
                    </div>
                </div>
            </Link>
        </Card>
    );
};
