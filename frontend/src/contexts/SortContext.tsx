import React, { createContext, useContext, useState, useCallback } from 'react';

type SortOrder = 'asc' | 'desc';

interface Sort {
  field: string;
  order: SortOrder;
}

interface SortContextType {
  sort: Sort | null;
  setSort: (field: string, order: SortOrder) => void;
  clearSort: () => void;
  toggleSort: (field: string) => void;
}

const SortContext = createContext<SortContextType | undefined>(undefined);

export const SortProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sort, setSortState] = useState<Sort | null>(null);

  const setSort = useCallback((field: string, order: SortOrder) => {
    setSortState({ field, order });
  }, []);

  const clearSort = useCallback(() => {
    setSortState(null);
  }, []);

  const toggleSort = useCallback(
    (field: string) => {
      if (sort?.field === field) {
        if (sort.order === 'asc') {
          setSortState({ field, order: 'desc' });
        } else {
          clearSort();
        }
      } else {
        setSortState({ field, order: 'asc' });
      }
    },
    [sort, clearSort]
  );

  return (
    <SortContext.Provider value={{ sort, setSort, clearSort, toggleSort }}>
      {children}
    </SortContext.Provider>
  );
};

export const useSort = () => {
  const context = useContext(SortContext);
  if (context === undefined) {
    throw new Error('useSort must be used within a SortProvider');
  }
  return context;
};
