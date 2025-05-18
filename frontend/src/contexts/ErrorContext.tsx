import React, { createContext, useContext, useState, useCallback } from 'react';

interface Error {
  id: string;
  message: string;
  code?: string;
  details?: any;
}

interface ErrorContextType {
  errors: Error[];
  addError: (error: Omit<Error, 'id'>) => void;
  removeError: (id: string) => void;
  clearErrors: () => void;
}

const ErrorContext = createContext<ErrorContextType | undefined>(undefined);

export const ErrorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [errors, setErrors] = useState<Error[]>([]);

  const addError = useCallback((error: Omit<Error, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newError = { ...error, id };
    setErrors((prev) => [...prev, newError]);
  }, []);

  const removeError = useCallback((id: string) => {
    setErrors((prev) => prev.filter((error) => error.id !== id));
  }, []);

  const clearErrors = useCallback(() => {
    setErrors([]);
  }, []);

  return (
    <ErrorContext.Provider value={{ errors, addError, removeError, clearErrors }}>
      {children}
    </ErrorContext.Provider>
  );
};

export const useError = () => {
  const context = useContext(ErrorContext);
  if (context === undefined) {
    throw new Error('useError must be used within an ErrorProvider');
  }
  return context;
};
