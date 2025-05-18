import React, { createContext, useContext, useState, useCallback } from 'react';

interface Filter {
  id: string;
  name: string;
  value: any;
  type: 'text' | 'number' | 'date' | 'select' | 'boolean';
  options?: { label: string; value: any }[];
}

interface FilterContextType {
  filters: Filter[];
  addFilter: (filter: Omit<Filter, 'id'>) => void;
  removeFilter: (id: string) => void;
  updateFilter: (id: string, value: any) => void;
  clearFilters: () => void;
  getFilterValue: (name: string) => any;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export const FilterProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [filters, setFilters] = useState<Filter[]>([]);

  const addFilter = useCallback((filter: Omit<Filter, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newFilter = { ...filter, id };
    setFilters((prev) => [...prev, newFilter]);
  }, []);

  const removeFilter = useCallback((id: string) => {
    setFilters((prev) => prev.filter((filter) => filter.id !== id));
  }, []);

  const updateFilter = useCallback((id: string, value: any) => {
    setFilters((prev) =>
      prev.map((filter) => (filter.id === id ? { ...filter, value } : filter))
    );
  }, []);

  const clearFilters = useCallback(() => {
    setFilters([]);
  }, []);

  const getFilterValue = useCallback(
    (name: string) => {
      const filter = filters.find((f) => f.name === name);
      return filter?.value;
    },
    [filters]
  );

  return (
    <FilterContext.Provider
      value={{ filters, addFilter, removeFilter, updateFilter, clearFilters, getFilterValue }}
    >
      {children}
    </FilterContext.Provider>
  );
};

export const useFilter = () => {
  const context = useContext(FilterContext);
  if (context === undefined) {
    throw new Error('useFilter must be used within a FilterProvider');
  }
  return context;
};
