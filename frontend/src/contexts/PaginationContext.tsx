import React, { createContext, useContext, useState, useCallback } from 'react';

interface Pagination {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

interface PaginationContextType {
  pagination: Pagination;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  setTotalItems: (totalItems: number) => void;
  nextPage: () => void;
  previousPage: () => void;
  goToPage: (page: number) => void;
}

const PaginationContext = createContext<PaginationContextType | undefined>(undefined);

export const PaginationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    pageSize: 10,
    totalItems: 0,
    totalPages: 0,
  });

  const setPage = useCallback((page: number) => {
    setPagination((prev) => ({ ...prev, page }));
  }, []);

  const setPageSize = useCallback((pageSize: number) => {
    setPagination((prev) => ({
      ...prev,
      pageSize,
      page: 1,
      totalPages: Math.ceil(prev.totalItems / pageSize),
    }));
  }, []);

  const setTotalItems = useCallback((totalItems: number) => {
    setPagination((prev) => ({
      ...prev,
      totalItems,
      totalPages: Math.ceil(totalItems / prev.pageSize),
    }));
  }, []);

  const nextPage = useCallback(() => {
    setPagination((prev) => {
      if (prev.page < prev.totalPages) {
        return { ...prev, page: prev.page + 1 };
      }
      return prev;
    });
  }, []);

  const previousPage = useCallback(() => {
    setPagination((prev) => {
      if (prev.page > 1) {
        return { ...prev, page: prev.page - 1 };
      }
      return prev;
    });
  }, []);

  const goToPage = useCallback((page: number) => {
    setPagination((prev) => {
      if (page >= 1 && page <= prev.totalPages) {
        return { ...prev, page };
      }
      return prev;
    });
  }, []);

  return (
    <PaginationContext.Provider
      value={{
        pagination,
        setPage,
        setPageSize,
        setTotalItems,
        nextPage,
        previousPage,
        goToPage,
      }}
    >
      {children}
    </PaginationContext.Provider>
  );
};

export const usePagination = () => {
  const context = useContext(PaginationContext);
  if (context === undefined) {
    throw new Error('usePagination must be used within a PaginationProvider');
  }
  return context;
};
