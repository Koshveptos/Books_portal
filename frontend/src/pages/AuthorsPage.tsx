import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { authorService } from '../services/author';
import { useAuth } from '../contexts/AuthContext';
import { Spinner } from '../components/Spinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { Author } from '../types/author';

export const AuthorsPage: React.FC = () => {
    const [authors, setAuthors] = useState<Author[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { hasRole } = useAuth();

    useEffect(() => {
        const fetchAuthors = async () => {
            try {
                const data = await authorService.getAuthors();
                setAuthors(data);
            } catch (err) {
                setError('Ошибка при загрузке авторов');
            } finally {
                setLoading(false);
            }
        };

        fetchAuthors();
    }, []);

    if (loading) return <Spinner />;
    if (error) return <ErrorMessage message={error} />;

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Авторы</h1>
                {(hasRole('admin') || hasRole('moderator')) && (
                    <Link
                        to="/authors/add"
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    >
                        Добавить автора
                    </Link>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {authors.map((author) => (
                    <Link
                        key={author.id}
                        to={`/authors/${author.id}`}
                        className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow"
                    >
                        <div className="p-6">
                            <h2 className="text-xl font-semibold text-gray-900 mb-2">
                                {author.name}
                            </h2>
                            {author.biography && (
                                <p className="text-gray-600 line-clamp-3">
                                    {author.biography}
                                </p>
                            )}
                        </div>
                    </Link>
                ))}
            </div>
        </div>
    );
};
