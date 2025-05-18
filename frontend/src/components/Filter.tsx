import React from 'react';
import { Select } from './Form';

interface FilterProps {
  categories: { id: number; name_categories: string }[];
  authors: { id: number; name: string }[];
  selectedCategory: string;
  selectedAuthor: string;
  onCategoryChange: (value: string) => void;
  onAuthorChange: (value: string) => void;
}

export const Filter: React.FC<FilterProps> = ({
  categories,
  authors,
  selectedCategory,
  selectedAuthor,
  onCategoryChange,
  onAuthorChange,
}) => {
  return (
    <div className="bg-white p-4 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Фильтры</h3>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Категория
          </label>
          <Select
            value={selectedCategory}
            onChange={(e) => onCategoryChange(e.target.value)}
            options={[
              { value: '', label: 'Все категории' },
              ...categories.map((category) => ({
                value: category.id.toString(),
                label: category.name_categories,
              })),
            ]}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Автор
          </label>
          <Select
            value={selectedAuthor}
            onChange={(e) => onAuthorChange(e.target.value)}
            options={[
              { value: '', label: 'Все авторы' },
              ...authors.map((author) => ({
                value: author.id.toString(),
                label: author.name,
              })),
            ]}
          />
        </div>
      </div>
    </div>
  );
};

export default Filter;
