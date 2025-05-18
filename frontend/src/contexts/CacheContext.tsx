import React, { createContext, useContext, useState, useCallback } from 'react';

interface CacheItem<T> {
  key: string;
  data: T;
  timestamp: number;
  expiresAt?: number;
}

interface CacheContextType {
  get: <T>(key: string) => T | null;
  set: <T>(key: string, data: T, expiresIn?: number) => void;
  remove: (key: string) => void;
  clear: () => void;
  has: (key: string) => boolean;
}

const CacheContext = createContext<CacheContextType | undefined>(undefined);

export const CacheProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [cache, setCache] = useState<Map<string, CacheItem<any>>>(new Map());

  const get = useCallback(
    <T,>(key: string): T | null => {
      const item = cache.get(key);
      if (!item) return null;

      if (item.expiresAt && item.expiresAt < Date.now()) {
        cache.delete(key);
        return null;
      }

      return item.data as T;
    },
    [cache]
  );

  const set = useCallback(
    <T,>(key: string, data: T, expiresIn?: number) => {
      const item: CacheItem<T> = {
        key,
        data,
        timestamp: Date.now(),
        expiresAt: expiresIn ? Date.now() + expiresIn : undefined,
      };
      setCache((prev) => new Map(prev).set(key, item));
    },
    []
  );

  const remove = useCallback((key: string) => {
    setCache((prev) => {
      const newCache = new Map(prev);
      newCache.delete(key);
      return newCache;
    });
  }, []);

  const clear = useCallback(() => {
    setCache(new Map());
  }, []);

  const has = useCallback(
    (key: string): boolean => {
      const item = cache.get(key);
      if (!item) return false;

      if (item.expiresAt && item.expiresAt < Date.now()) {
        cache.delete(key);
        return false;
      }

      return true;
    },
    [cache]
  );

  return (
    <CacheContext.Provider value={{ get, set, remove, clear, has }}>
      {children}
    </CacheContext.Provider>
  );
};

export const useCache = () => {
  const context = useContext(CacheContext);
  if (context === undefined) {
    throw new Error('useCache must be used within a CacheProvider');
  }
  return context;
};
