import React, { createContext, useContext, useState, useCallback } from 'react';

interface Sound {
  id: string;
  src: string;
  volume: number;
  loop: boolean;
  autoplay: boolean;
}

interface SoundContextType {
  sounds: Sound[];
  addSound: (sound: Omit<Sound, 'id'>) => string;
  removeSound: (id: string) => void;
  playSound: (id: string) => void;
  pauseSound: (id: string) => void;
  stopSound: (id: string) => void;
  setVolume: (id: string, volume: number) => void;
  isMuted: boolean;
  setIsMuted: (isMuted: boolean) => void;
}

const SoundContext = createContext<SoundContextType | undefined>(undefined);

export const SoundProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sounds, setSounds] = useState<Sound[]>([]);
  const [isMuted, setIsMuted] = useState(false);

  const addSound = useCallback((sound: Omit<Sound, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newSound = { ...sound, id };
    setSounds((prev) => [...prev, newSound]);
    return id;
  }, []);

  const removeSound = useCallback((id: string) => {
    setSounds((prev) => prev.filter((sound) => sound.id !== id));
  }, []);

  const playSound = useCallback((id: string) => {
    const sound = sounds.find((s) => s.id === id);
    if (sound) {
      const audio = new Audio(sound.src);
      audio.volume = sound.volume;
      audio.loop = sound.loop;
      audio.play();
    }
  }, [sounds]);

  const pauseSound = useCallback((id: string) => {
    const sound = sounds.find((s) => s.id === id);
    if (sound) {
      const audio = new Audio(sound.src);
      audio.pause();
    }
  }, [sounds]);

  const stopSound = useCallback((id: string) => {
    const sound = sounds.find((s) => s.id === id);
    if (sound) {
      const audio = new Audio(sound.src);
      audio.pause();
      audio.currentTime = 0;
    }
  }, [sounds]);

  const setVolume = useCallback((id: string, volume: number) => {
    setSounds((prev) =>
      prev.map((sound) => (sound.id === id ? { ...sound, volume } : sound))
    );
  }, []);

  return (
    <SoundContext.Provider
      value={{
        sounds,
        addSound,
        removeSound,
        playSound,
        pauseSound,
        stopSound,
        setVolume,
        isMuted,
        setIsMuted,
      }}
    >
      {children}
    </SoundContext.Provider>
  );
};

export const useSound = () => {
  const context = useContext(SoundContext);
  if (context === undefined) {
    throw new Error('useSound must be used within a SoundProvider');
  }
  return context;
};
