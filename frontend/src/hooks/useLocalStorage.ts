import { useState, useEffect } from 'react';

function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T) => void] {
  // Получаем сохраненное значение или используем initialValue
  const readValue = (): T => {
    if (typeof window === 'undefined') {
      return initialValue;
    }

    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Ошибка при чтении localStorage ключа "${key}":`, error);
      return initialValue;
    }
  };

  const [storedValue, setStoredValue] = useState<T>(readValue);

  // Функция для сохранения значения
  const setValue = (value: T) => {
    if (typeof window === 'undefined') {
      console.warn(`Невозможно сохранить значение в localStorage (окружение не браузерное).`);
      return;
    }

    try {
      // Сохранить в состояние
      setStoredValue(value);

      // Сохранить в localStorage
      window.localStorage.setItem(key, JSON.stringify(value));

      // Отправить событие для других компонентов, использующих тот же ключ
      window.dispatchEvent(new Event('local-storage'));
    } catch (error) {
      console.warn(`Ошибка при записи localStorage ключа "${key}":`, error);
    }
  };

  // Слушаем изменения в других вкладках/окнах
  useEffect(() => {
    const handleStorageChange = () => {
      setStoredValue(readValue());
    };

    // Это событие срабатывает только в других вкладках
    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('local-storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('local-storage', handleStorageChange);
    };
  }, []);

  return [storedValue, setValue];
}

export default useLocalStorage;
