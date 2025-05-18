import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

type KeyHandler = (event: KeyboardEvent) => void;

interface KeyboardContextType {
  pressedKeys: Set<string>;
  addKeyHandler: (key: string, handler: KeyHandler) => void;
  removeKeyHandler: (key: string, handler: KeyHandler) => void;
  isKeyPressed: (key: string) => boolean;
}

const KeyboardContext = createContext<KeyboardContextType | undefined>(undefined);

export const KeyboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [pressedKeys, setPressedKeys] = useState<Set<string>>(new Set());
  const [keyHandlers, setKeyHandlers] = useState<Map<string, Set<KeyHandler>>>(new Map());

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      setPressedKeys((prev) => {
        const newSet = new Set(prev);
        newSet.add(key);
        return newSet;
      });

      const handlers = keyHandlers.get(key);
      if (handlers) {
        handlers.forEach((handler) => handler(event));
      }
    },
    [keyHandlers]
  );

  const handleKeyUp = useCallback((event: KeyboardEvent) => {
    const key = event.key.toLowerCase();
    setPressedKeys((prev) => {
      const newSet = new Set(prev);
      newSet.delete(key);
      return newSet;
    });
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [handleKeyDown, handleKeyUp]);

  const addKeyHandler = useCallback((key: string, handler: KeyHandler) => {
    setKeyHandlers((prev) => {
      const newMap = new Map(prev);
      const handlers = newMap.get(key) || new Set();
      handlers.add(handler);
      newMap.set(key, handlers);
      return newMap;
    });
  }, []);

  const removeKeyHandler = useCallback((key: string, handler: KeyHandler) => {
    setKeyHandlers((prev) => {
      const newMap = new Map(prev);
      const handlers = newMap.get(key);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          newMap.delete(key);
        }
      }
      return newMap;
    });
  }, []);

  const isKeyPressed = useCallback(
    (key: string) => {
      return pressedKeys.has(key.toLowerCase());
    },
    [pressedKeys]
  );

  return (
    <KeyboardContext.Provider
      value={{
        pressedKeys,
        addKeyHandler,
        removeKeyHandler,
        isKeyPressed,
      }}
    >
      {children}
    </KeyboardContext.Provider>
  );
};

export const useKeyboard = () => {
  const context = useContext(KeyboardContext);
  if (context === undefined) {
    throw new Error('useKeyboard must be used within a KeyboardProvider');
  }
  return context;
};
