import React from 'react';
import { Select } from './Form';

interface SortProps {
  value: string;
  onChange: (value: string) => void;
}

export const Sort: React.FC<SortProps> = ({ value, onChange }) => {
  const sortOptions = [
    { value: 'title_asc', label: 'По названию (А-Я)' },
    { value: 'title_desc', label: 'По названию (Я-А)' },
    { value: 'year_asc', label: 'По году (по возрастанию)' },
    { value: 'year_desc', label: 'По году (по убыванию)' },
    { value: 'rating_asc', label: 'По рейтингу (по возрастанию)' },
    { value: 'rating_desc', label: 'По рейтингу (по убыванию)' },
  ];

  return (
    <div className="bg-white p-4 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Сортировка</h3>
      <Select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        options={sortOptions}
      />
    </div>
  );
};

export default Sort;
