import React, { createContext, useContext, useState, useCallback } from 'react';

interface HistoryItem {
  id: string;
  path: string;
  title: string;
  timestamp: number;
}

interface HistoryContextType {
  history: HistoryItem[];
  addToHistory: (path: string, title: string) => void;
  removeFromHistory: (id: string) => void;
  clearHistory: () => void;
  getPreviousPage: () => HistoryItem | undefined;
  getNextPage: () => HistoryItem | undefined;
}

const HistoryContext = createContext<HistoryContextType | undefined>(undefined);

export const HistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(-1);

  const addToHistory = useCallback((path: string, title: string) => {
    const newItem: HistoryItem = {
      id: Math.random().toString(36).substr(2, 9),
      path,
      title,
      timestamp: Date.now(),
    };

    setHistory((prev) => {
      const newHistory = prev.slice(0, currentIndex + 1);
      newHistory.push(newItem);
      setCurrentIndex(newHistory.length - 1);
      return newHistory;
    });
  }, [currentIndex]);

  const removeFromHistory = useCallback((id: string) => {
    setHistory((prev) => {
      const newHistory = prev.filter((item) => item.id !== id);
      setCurrentIndex(Math.min(currentIndex, newHistory.length - 1));
      return newHistory;
    });
  }, [currentIndex]);

  const clearHistory = useCallback(() => {
    setHistory([]);
    setCurrentIndex(-1);
  }, []);

  const getPreviousPage = useCallback(() => {
    if (currentIndex > 0) {
      return history[currentIndex - 1];
    }
    return undefined;
  }, [history, currentIndex]);

  const getNextPage = useCallback(() => {
    if (currentIndex < history.length - 1) {
      return history[currentIndex + 1];
    }
    return undefined;
  }, [history, currentIndex]);

  return (
    <HistoryContext.Provider
      value={{
        history,
        addToHistory,
        removeFromHistory,
        clearHistory,
        getPreviousPage,
        getNextPage,
      }}
    >
      {children}
    </HistoryContext.Provider>
  );
};

export const useHistory = () => {
  const context = useContext(HistoryContext);
  if (context === undefined) {
    throw new Error('useHistory must be used within a HistoryProvider');
  }
  return context;
};
