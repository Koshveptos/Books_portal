import React from 'react';
import { Link } from 'react-router-dom';
import { Tag, Book } from '../types';

interface TagCardProps {
  tag: Tag & { description?: string; books?: Book[] };
}

export const TagCard: React.FC<TagCardProps> = ({ tag }) => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="p-4">
        <Link to={`/tags/${tag.id}`} className="block">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {tag.name}
          </h3>
        </Link>

        {tag.description && (
          <p className="text-gray-700 text-sm mb-4 line-clamp-3">
            {tag.description}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          {tag.books?.map((book: Book) => (
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

export default TagCard;
