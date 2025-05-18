import React from 'react';
import { Link } from 'react-router-dom';
import { User, Book } from '../types';

interface UserCardProps {
  user: User & { favorite_books?: Book[] };
}

export const UserCard: React.FC<UserCardProps> = ({ user }) => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="p-4">
        <Link to={`/users/${user.id}`} className="block">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {user.email}
          </h3>
        </Link>

        <div className="flex flex-wrap gap-2">
          {user.favorite_books?.map((book: Book) => (
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

export default UserCard;
