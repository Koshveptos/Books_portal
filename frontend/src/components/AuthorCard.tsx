import React from 'react';
import { Link } from 'react-router-dom';
import { Author, Book } from '../types';

interface AuthorCardProps {
  author: Author & { books?: Book[] };
}

export const AuthorCard: React.FC<AuthorCardProps> = ({ author }) => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="p-4">
        <Link to={`/authors/${author.id}`} className="block">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {author.name}
          </h3>
        </Link>

        {author.biography && (
          <p className="text-gray-700 text-sm mb-4 line-clamp-3">
            {author.biography}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          {author.books?.map((book: Book) => (
            <Link
              key={book.id}
              to={`/books/${book.id}`}
              className="inline-block bg-gray-100 rounded-full px-3 py-1 text-sm font-semibold text-gray-600 hover:bg-gray-200"
            >
              {book.title}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AuthorCard;
