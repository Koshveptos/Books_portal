import React, { createContext, useContext, useReducer, useCallback } from 'react';

interface State {
  books: any[];
  authors: any[];
  categories: any[];
  selectedBook: any | null;
  selectedAuthor: any | null;
  selectedCategory: any | null;
  filters: {
    search: string;
    category: string | null;
    author: string | null;
    sortBy: string;
    sortOrder: 'asc' | 'desc';
  };
}

type Action =
  | { type: 'SET_BOOKS'; payload: any[] }
  | { type: 'SET_AUTHORS'; payload: any[] }
  | { type: 'SET_CATEGORIES'; payload: any[] }
  | { type: 'SET_SELECTED_BOOK'; payload: any | null }
  | { type: 'SET_SELECTED_AUTHOR'; payload: any | null }
  | { type: 'SET_SELECTED_CATEGORY'; payload: any | null }
  | { type: 'SET_FILTERS'; payload: Partial<State['filters']> }
  | { type: 'RESET_FILTERS' };

const initialState: State = {
  books: [],
  authors: [],
  categories: [],
  selectedBook: null,
  selectedAuthor: null,
  selectedCategory: null,
  filters: {
    search: '',
    category: null,
    author: null,
    sortBy: 'title',
    sortOrder: 'asc',
  },
};

const reducer = (state: State, action: Action): State => {
  switch (action.type) {
    case 'SET_BOOKS':
      return { ...state, books: action.payload };
    case 'SET_AUTHORS':
      return { ...state, authors: action.payload };
    case 'SET_CATEGORIES':
      return { ...state, categories: action.payload };
    case 'SET_SELECTED_BOOK':
      return { ...state, selectedBook: action.payload };
    case 'SET_SELECTED_AUTHOR':
      return { ...state, selectedAuthor: action.payload };
    case 'SET_SELECTED_CATEGORY':
      return { ...state, selectedCategory: action.payload };
    case 'SET_FILTERS':
      return {
        ...state,
        filters: { ...state.filters, ...action.payload },
      };
    case 'RESET_FILTERS':
      return {
        ...state,
        filters: initialState.filters,
      };
    default:
      return state;
  }
};

interface StateContextType {
  state: State;
  setBooks: (books: any[]) => void;
  setAuthors: (authors: any[]) => void;
  setCategories: (categories: any[]) => void;
  setSelectedBook: (book: any | null) => void;
  setSelectedAuthor: (author: any | null) => void;
  setSelectedCategory: (category: any | null) => void;
  setFilters: (filters: Partial<State['filters']>) => void;
  resetFilters: () => void;
}

const StateContext = createContext<StateContextType | undefined>(undefined);

export const StateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialState);

  const setBooks = useCallback((books: any[]) => {
    dispatch({ type: 'SET_BOOKS', payload: books });
  }, []);

  const setAuthors = useCallback((authors: any[]) => {
    dispatch({ type: 'SET_AUTHORS', payload: authors });
  }, []);

  const setCategories = useCallback((categories: any[]) => {
    dispatch({ type: 'SET_CATEGORIES', payload: categories });
  }, []);

  const setSelectedBook = useCallback((book: any | null) => {
    dispatch({ type: 'SET_SELECTED_BOOK', payload: book });
  }, []);

  const setSelectedAuthor = useCallback((author: any | null) => {
    dispatch({ type: 'SET_SELECTED_AUTHOR', payload: author });
  }, []);

  const setSelectedCategory = useCallback((category: any | null) => {
    dispatch({ type: 'SET_SELECTED_CATEGORY', payload: category });
  }, []);

  const setFilters = useCallback((filters: Partial<State['filters']>) => {
    dispatch({ type: 'SET_FILTERS', payload: filters });
  }, []);

  const resetFilters = useCallback(() => {
    dispatch({ type: 'RESET_FILTERS' });
  }, []);

  return (
    <StateContext.Provider
      value={{
        state,
        setBooks,
        setAuthors,
        setCategories,
        setSelectedBook,
        setSelectedAuthor,
        setSelectedCategory,
        setFilters,
        resetFilters,
      }}
    >
      {children}
    </StateContext.Provider>
  );
};

export const useState = () => {
  const context = useContext(StateContext);
  if (context === undefined) {
    throw new Error('useState must be used within a StateProvider');
  }
  return context;
};
