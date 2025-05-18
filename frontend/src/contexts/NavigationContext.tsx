import React, { createContext, useContext, useState, useCallback } from 'react';

interface NavigationItem {
  id: string;
  label: string;
  path: string;
  icon?: React.ReactNode;
  children?: NavigationItem[];
}

interface NavigationContextType {
  navigationItems: NavigationItem[];
  activePath: string;
  setActivePath: (path: string) => void;
  addNavigationItem: (item: NavigationItem) => void;
  removeNavigationItem: (id: string) => void;
  updateNavigationItem: (id: string, item: Partial<NavigationItem>) => void;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

export const NavigationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [navigationItems, setNavigationItems] = useState<NavigationItem[]>([]);
  const [activePath, setActivePath] = useState('');

  const addNavigationItem = useCallback((item: NavigationItem) => {
    setNavigationItems((prev) => [...prev, item]);
  }, []);

  const removeNavigationItem = useCallback((id: string) => {
    setNavigationItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const updateNavigationItem = useCallback((id: string, item: Partial<NavigationItem>) => {
    setNavigationItems((prev) =>
      prev.map((navItem) => (navItem.id === id ? { ...navItem, ...item } : navItem))
    );
  }, []);

  return (
    <NavigationContext.Provider
      value={{
        navigationItems,
        activePath,
        setActivePath,
        addNavigationItem,
        removeNavigationItem,
        updateNavigationItem,
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
};

export const useNavigation = () => {
  const context = useContext(NavigationContext);
  if (context === undefined) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
};
