import React from 'react';
import { Link } from 'react-router-dom';
import { Category, Book } from '../types';

interface CategoryCardProps {
  category: Category & { books?: Book[] };
}

export const CategoryCard: React.FC<CategoryCardProps> = ({ category }) => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="p-4">
        <Link to={`/categories/${category.id}`} className="block">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {category.name_categories}
          </h3>
        </Link>

        {category.description && (
          <p className="text-gray-700 text-sm mb-4 line-clamp-3">
            {category.description}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          {category.books?.map((book: Book) => (
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

export default CategoryCard;
