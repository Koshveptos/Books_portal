import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

interface MousePosition {
  x: number;
  y: number;
}

interface MouseContextType {
  position: MousePosition;
  isLeftButtonPressed: boolean;
  isRightButtonPressed: boolean;
  isMiddleButtonPressed: boolean;
  addMouseMoveHandler: (handler: (position: MousePosition) => void) => void;
  removeMouseMoveHandler: (handler: (position: MousePosition) => void) => void;
  addMouseDownHandler: (button: 'left' | 'right' | 'middle', handler: () => void) => void;
  removeMouseDownHandler: (button: 'left' | 'right' | 'middle', handler: () => void) => void;
  addMouseUpHandler: (button: 'left' | 'right' | 'middle', handler: () => void) => void;
  removeMouseUpHandler: (button: 'left' | 'right' | 'middle', handler: () => void) => void;
}

const MouseContext = createContext<MouseContextType | undefined>(undefined);

export const MouseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [position, setPosition] = useState<MousePosition>({ x: 0, y: 0 });
  const [isLeftButtonPressed, setIsLeftButtonPressed] = useState(false);
  const [isRightButtonPressed, setIsRightButtonPressed] = useState(false);
  const [isMiddleButtonPressed, setIsMiddleButtonPressed] = useState(false);
  const [moveHandlers, setMoveHandlers] = useState<Set<(position: MousePosition) => void>>(new Set());
  const [downHandlers, setDownHandlers] = useState<{
    left: Set<() => void>;
    right: Set<() => void>;
    middle: Set<() => void>;
  }>({
    left: new Set(),
    right: new Set(),
    middle: new Set(),
  });
  const [upHandlers, setUpHandlers] = useState<{
    left: Set<() => void>;
    right: Set<() => void>;
    middle: Set<() => void>;
  }>({
    left: new Set(),
    right: new Set(),
    middle: new Set(),
  });

  const handleMouseMove = useCallback(
    (event: MouseEvent) => {
      const newPosition = { x: event.clientX, y: event.clientY };
      setPosition(newPosition);
      moveHandlers.forEach((handler) => handler(newPosition));
    },
    [moveHandlers]
  );

  const handleMouseDown = useCallback(
    (event: MouseEvent) => {
      switch (event.button) {
        case 0:
          setIsLeftButtonPressed(true);
          downHandlers.left.forEach((handler) => handler());
          break;
        case 1:
          setIsMiddleButtonPressed(true);
          downHandlers.middle.forEach((handler) => handler());
          break;
        case 2:
          setIsRightButtonPressed(true);
          downHandlers.right.forEach((handler) => handler());
          break;
      }
    },
    [downHandlers]
  );

  const handleMouseUp = useCallback(
    (event: MouseEvent) => {
      switch (event.button) {
        case 0:
          setIsLeftButtonPressed(false);
          upHandlers.left.forEach((handler) => handler());
          break;
        case 1:
          setIsMiddleButtonPressed(false);
          upHandlers.middle.forEach((handler) => handler());
          break;
        case 2:
          setIsRightButtonPressed(false);
          upHandlers.right.forEach((handler) => handler());
          break;
      }
    },
    [upHandlers]
  );

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseDown, handleMouseUp]);

  const addMouseMoveHandler = useCallback((handler: (position: MousePosition) => void) => {
    setMoveHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.add(handler);
      return newSet;
    });
  }, []);

  const removeMouseMoveHandler = useCallback((handler: (position: MousePosition) => void) => {
    setMoveHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.delete(handler);
      return newSet;
    });
  }, []);

  const addMouseDownHandler = useCallback(
    (button: 'left' | 'right' | 'middle', handler: () => void) => {
      setDownHandlers((prev) => ({
        ...prev,
        [button]: new Set(Array.from(prev[button]).concat(handler)),
      }));
    },
    []
  );

  const removeMouseDownHandler = useCallback(
    (button: 'left' | 'right' | 'middle', handler: () => void) => {
      setDownHandlers((prev) => ({
        ...prev,
        [button]: new Set(Array.from(prev[button]).filter((h) => h !== handler)),
      }));
    },
    []
  );

  const addMouseUpHandler = useCallback(
    (button: 'left' | 'right' | 'middle', handler: () => void) => {
      setUpHandlers((prev) => ({
        ...prev,
        [button]: new Set(Array.from(prev[button]).concat(handler)),
      }));
    },
    []
  );

  const removeMouseUpHandler = useCallback(
    (button: 'left' | 'right' | 'middle', handler: () => void) => {
      setUpHandlers((prev) => ({
        ...prev,
        [button]: new Set(Array.from(prev[button]).filter((h) => h !== handler)),
      }));
    },
    []
  );

  return (
    <MouseContext.Provider
      value={{
        position,
        isLeftButtonPressed,
        isRightButtonPressed,
        isMiddleButtonPressed,
        addMouseMoveHandler,
        removeMouseMoveHandler,
        addMouseDownHandler,
        removeMouseDownHandler,
        addMouseUpHandler,
        removeMouseUpHandler,
      }}
    >
      {children}
    </MouseContext.Provider>
  );
};

export const useMouse = () => {
  const context = useContext(MouseContext);
  if (context === undefined) {
    throw new Error('useMouse must be used within a MouseProvider');
  }
  return context;
};
