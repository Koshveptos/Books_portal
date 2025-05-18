import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

interface TouchPoint {
  id: number;
  x: number;
  y: number;
}

interface TouchContextType {
  touchPoints: TouchPoint[];
  addTouchStartHandler: (handler: (point: TouchPoint) => void) => void;
  removeTouchStartHandler: (handler: (point: TouchPoint) => void) => void;
  addTouchMoveHandler: (handler: (point: TouchPoint) => void) => void;
  removeTouchMoveHandler: (handler: (point: TouchPoint) => void) => void;
  addTouchEndHandler: (handler: (point: TouchPoint) => void) => void;
  removeTouchEndHandler: (handler: (point: TouchPoint) => void) => void;
}

const TouchContext = createContext<TouchContextType | undefined>(undefined);

export const TouchProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [touchPoints, setTouchPoints] = useState<TouchPoint[]>([]);
  const [startHandlers, setStartHandlers] = useState<Set<(point: TouchPoint) => void>>(new Set());
  const [moveHandlers, setMoveHandlers] = useState<Set<(point: TouchPoint) => void>>(new Set());
  const [endHandlers, setEndHandlers] = useState<Set<(point: TouchPoint) => void>>(new Set());

  const handleTouchStart = useCallback(
    (event: TouchEvent) => {
      const newPoints: TouchPoint[] = Array.from(event.touches).map((touch) => ({
        id: touch.identifier,
        x: touch.clientX,
        y: touch.clientY,
      }));
      setTouchPoints(newPoints);
      newPoints.forEach((point) => {
        startHandlers.forEach((handler) => handler(point));
      });
    },
    [startHandlers]
  );

  const handleTouchMove = useCallback(
    (event: TouchEvent) => {
      const newPoints: TouchPoint[] = Array.from(event.touches).map((touch) => ({
        id: touch.identifier,
        x: touch.clientX,
        y: touch.clientY,
      }));
      setTouchPoints(newPoints);
      newPoints.forEach((point) => {
        moveHandlers.forEach((handler) => handler(point));
      });
    },
    [moveHandlers]
  );

  const handleTouchEnd = useCallback(
    (event: TouchEvent) => {
      const newPoints: TouchPoint[] = Array.from(event.touches).map((touch) => ({
        id: touch.identifier,
        x: touch.clientX,
        y: touch.clientY,
      }));
      setTouchPoints(newPoints);
      const removedPoints = touchPoints.filter(
        (point) => !newPoints.some((newPoint) => newPoint.id === point.id)
      );
      removedPoints.forEach((point) => {
        endHandlers.forEach((handler) => handler(point));
      });
    },
    [touchPoints, endHandlers]
  );

  useEffect(() => {
    window.addEventListener('touchstart', handleTouchStart);
    window.addEventListener('touchmove', handleTouchMove);
    window.addEventListener('touchend', handleTouchEnd);

    return () => {
      window.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleTouchStart, handleTouchMove, handleTouchEnd]);

  const addTouchStartHandler = useCallback((handler: (point: TouchPoint) => void) => {
    setStartHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.add(handler);
      return newSet;
    });
  }, []);

  const removeTouchStartHandler = useCallback((handler: (point: TouchPoint) => void) => {
    setStartHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.delete(handler);
      return newSet;
    });
  }, []);

  const addTouchMoveHandler = useCallback((handler: (point: TouchPoint) => void) => {
    setMoveHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.add(handler);
      return newSet;
    });
  }, []);

  const removeTouchMoveHandler = useCallback((handler: (point: TouchPoint) => void) => {
    setMoveHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.delete(handler);
      return newSet;
    });
  }, []);

  const addTouchEndHandler = useCallback((handler: (point: TouchPoint) => void) => {
    setEndHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.add(handler);
      return newSet;
    });
  }, []);

  const removeTouchEndHandler = useCallback((handler: (point: TouchPoint) => void) => {
    setEndHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.delete(handler);
      return newSet;
    });
  }, []);

  return (
    <TouchContext.Provider
      value={{
        touchPoints,
        addTouchStartHandler,
        removeTouchStartHandler,
        addTouchMoveHandler,
        removeTouchMoveHandler,
        addTouchEndHandler,
        removeTouchEndHandler,
      }}
    >
      {children}
    </TouchContext.Provider>
  );
};

export const useTouch = () => {
  const context = useContext(TouchContext);
  if (context === undefined) {
    throw new Error('useTouch must be used within a TouchProvider');
  }
  return context;
};
