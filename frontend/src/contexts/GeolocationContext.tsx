import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

interface GeolocationPosition {
  coords: {
    latitude: number;
    longitude: number;
    accuracy: number;
    altitude: number | null;
    altitudeAccuracy: number | null;
    heading: number | null;
    speed: number | null;
  };
  timestamp: number;
}

interface GeolocationContextType {
  position: GeolocationPosition | null;
  error: GeolocationPositionError | null;
  isSupported: boolean;
  startWatching: () => void;
  stopWatching: () => void;
}

const GeolocationContext = createContext<GeolocationContextType | undefined>(undefined);

export const GeolocationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [position, setPosition] = useState<GeolocationPosition | null>(null);
  const [error, setError] = useState<GeolocationPositionError | null>(null);
  const [isSupported] = useState<boolean>('geolocation' in navigator);
  const [watchId, setWatchId] = useState<number | null>(null);

  const handleSuccess = useCallback((position: GeolocationPosition) => {
    setPosition(position);
    setError(null);
  }, []);

  const handleError = useCallback((error: GeolocationPositionError) => {
    setError(error);
    setPosition(null);
  }, []);

  const startWatching = useCallback(() => {
    if (isSupported && !watchId) {
      const id = navigator.geolocation.watchPosition(handleSuccess, handleError, {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      });
      setWatchId(id);
    }
  }, [isSupported, watchId, handleSuccess, handleError]);

  const stopWatching = useCallback(() => {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      setWatchId(null);
    }
  }, [watchId]);

  useEffect(() => {
    return () => {
      if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
      }
    };
  }, [watchId]);

  return (
    <GeolocationContext.Provider
      value={{
        position,
        error,
        isSupported,
        startWatching,
        stopWatching,
      }}
    >
      {children}
    </GeolocationContext.Provider>
  );
};

export const useGeolocation = () => {
  const context = useContext(GeolocationContext);
  if (context === undefined) {
    throw new Error('useGeolocation must be used within a GeolocationProvider');
  }
  return context;
};
