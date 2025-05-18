import React, { createContext, useContext, useState, useCallback } from 'react';

interface Modal {
  id: string;
  component: React.ReactNode;
  props?: Record<string, any>;
}

interface ModalContextType {
  modals: Modal[];
  openModal: (component: React.ReactNode, props?: Record<string, any>) => string;
  closeModal: (id: string) => void;
  closeAllModals: () => void;
}

const ModalContext = createContext<ModalContextType | undefined>(undefined);

export const ModalProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [modals, setModals] = useState<Modal[]>([]);

  const openModal = useCallback((component: React.ReactNode, props?: Record<string, any>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newModal = { id, component, props };
    setModals((prev) => [...prev, newModal]);
    return id;
  }, []);

  const closeModal = useCallback((id: string) => {
    setModals((prev) => prev.filter((modal) => modal.id !== id));
  }, []);

  const closeAllModals = useCallback(() => {
    setModals([]);
  }, []);

  return (
    <ModalContext.Provider value={{ modals, openModal, closeModal, closeAllModals }}>
      {children}
    </ModalContext.Provider>
  );
};

export const useModal = () => {
  const context = useContext(ModalContext);
  if (context === undefined) {
    throw new Error('useModal must be used within a ModalProvider');
  }
  return context;
};
