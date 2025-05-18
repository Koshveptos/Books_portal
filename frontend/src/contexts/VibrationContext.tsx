import React, { createContext, useContext, useState, useCallback } from 'react';

interface VibrationContextType {
  isSupported: boolean;
  vibrate: (pattern: number | number[]) => void;
  stopVibration: () => void;
}

const VibrationContext = createContext<VibrationContextType | undefined>(undefined);

export const VibrationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isSupported] = useState<boolean>('vibrate' in navigator);

  const vibrate = useCallback((pattern: number | number[]) => {
    if (isSupported) {
      navigator.vibrate(pattern);
    }
  }, [isSupported]);

  const stopVibration = useCallback(() => {
    if (isSupported) {
      navigator.vibrate(0);
    }
  }, [isSupported]);

  return (
    <VibrationContext.Provider
      value={{
        isSupported,
        vibrate,
        stopVibration,
      }}
    >
      {children}
    </VibrationContext.Provider>
  );
};

export const useVibration = () => {
  const context = useContext(VibrationContext);
  if (context === undefined) {
    throw new Error('useVibration must be used within a VibrationProvider');
  }
  return context;
};
