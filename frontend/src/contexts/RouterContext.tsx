import React, { createContext, useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

interface RouterContextType {
  navigate: ReturnType<typeof useNavigate>;
  location: ReturnType<typeof useLocation>;
}

const RouterContext = createContext<RouterContextType | undefined>(undefined);

export const RouterProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <RouterContext.Provider value={{ navigate, location }}>
      {children}
    </RouterContext.Provider>
  );
};

export const useRouter = () => {
  const context = useContext(RouterContext);
  if (context === undefined) {
    throw new Error('useRouter must be used within a RouterProvider');
  }
  return context;
};
