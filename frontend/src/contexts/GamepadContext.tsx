import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

interface GamepadButton {
  pressed: boolean;
  value: number;
}

interface GamepadState {
  id: string;
  buttons: GamepadButton[];
  axes: number[];
  connected: boolean;
}

interface GamepadContextType {
  gamepads: GamepadState[];
  addGamepadHandler: (handler: (gamepad: GamepadState) => void) => void;
  removeGamepadHandler: (handler: (gamepad: GamepadState) => void) => void;
  isGamepadConnected: (id: string) => boolean;
}

const GamepadContext = createContext<GamepadContextType | undefined>(undefined);

export const GamepadProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [gamepads, setGamepads] = useState<GamepadState[]>([]);
  const [handlers, setHandlers] = useState<Set<(gamepad: GamepadState) => void>>(new Set());

  const updateGamepads = useCallback(() => {
    const gamepadList = Array.from(navigator.getGamepads()).filter((gamepad): gamepad is Gamepad => gamepad !== null);
    const newGamepads = gamepadList.map((gamepad) => ({
      id: gamepad.id,
      buttons: Array.from(gamepad.buttons).map((button) => ({
        pressed: button.pressed,
        value: button.value,
      })),
      axes: Array.from(gamepad.axes),
      connected: gamepad.connected,
    }));
    setGamepads(newGamepads);
    newGamepads.forEach((gamepad) => {
      handlers.forEach((handler) => handler(gamepad));
    });
  }, [handlers]);

  useEffect(() => {
    const handleGamepadConnected = (event: GamepadEvent) => {
      updateGamepads();
    };

    const handleGamepadDisconnected = (event: GamepadEvent) => {
      updateGamepads();
    };

    window.addEventListener('gamepadconnected', handleGamepadConnected);
    window.addEventListener('gamepaddisconnected', handleGamepadDisconnected);

    const animationFrame = requestAnimationFrame(function gameLoop() {
      updateGamepads();
      requestAnimationFrame(gameLoop);
    });

    return () => {
      window.removeEventListener('gamepadconnected', handleGamepadConnected);
      window.removeEventListener('gamepaddisconnected', handleGamepadDisconnected);
      cancelAnimationFrame(animationFrame);
    };
  }, [updateGamepads]);

  const addGamepadHandler = useCallback((handler: (gamepad: GamepadState) => void) => {
    setHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.add(handler);
      return newSet;
    });
  }, []);

  const removeGamepadHandler = useCallback((handler: (gamepad: GamepadState) => void) => {
    setHandlers((prev) => {
      const newSet = new Set(prev);
      newSet.delete(handler);
      return newSet;
    });
  }, []);

  const isGamepadConnected = useCallback(
    (id: string) => {
      return gamepads.some((gamepad) => gamepad.id === id && gamepad.connected);
    },
    [gamepads]
  );

  return (
    <GamepadContext.Provider
      value={{
        gamepads,
        addGamepadHandler,
        removeGamepadHandler,
        isGamepadConnected,
      }}
    >
      {children}
    </GamepadContext.Provider>
  );
};

export const useGamepad = () => {
  const context = useContext(GamepadContext);
  if (context === undefined) {
    throw new Error('useGamepad must be used within a GamepadProvider');
  }
  return context;
};
