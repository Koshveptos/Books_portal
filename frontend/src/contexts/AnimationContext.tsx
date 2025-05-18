import React, { createContext, useContext, useState, useCallback } from 'react';

interface Animation {
  id: string;
  type: string;
  duration: number;
  delay?: number;
  easing?: string;
  onComplete?: () => void;
}

interface AnimationContextType {
  animations: Animation[];
  addAnimation: (animation: Omit<Animation, 'id'>) => string;
  removeAnimation: (id: string) => void;
  clearAnimations: () => void;
  isAnimating: boolean;
  setIsAnimating: (isAnimating: boolean) => void;
}

const AnimationContext = createContext<AnimationContextType | undefined>(undefined);

export const AnimationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [animations, setAnimations] = useState<Animation[]>([]);
  const [isAnimating, setIsAnimating] = useState(false);

  const addAnimation = useCallback((animation: Omit<Animation, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newAnimation = { ...animation, id };
    setAnimations((prev) => [...prev, newAnimation]);
    return id;
  }, []);

  const removeAnimation = useCallback((id: string) => {
    setAnimations((prev) => prev.filter((animation) => animation.id !== id));
  }, []);

  const clearAnimations = useCallback(() => {
    setAnimations([]);
  }, []);

  return (
    <AnimationContext.Provider
      value={{
        animations,
        addAnimation,
        removeAnimation,
        clearAnimations,
        isAnimating,
        setIsAnimating,
      }}
    >
      {children}
    </AnimationContext.Provider>
  );
};

export const useAnimation = () => {
  const context = useContext(AnimationContext);
  if (context === undefined) {
    throw new Error('useAnimation must be used within an AnimationProvider');
  }
  return context;
};
