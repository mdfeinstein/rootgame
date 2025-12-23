import { createContext, useState } from "react";

const GameContext = createContext<any>({});

const GameProvider = ({ children }: { children: React.ReactNode }) => {
  const [gameId, setGameId] = useState<number | null>(1);

  return (
    <GameContext.Provider
      value={{
        gameId,
        setGameId,
      }}
    >
      {children}
    </GameContext.Provider>
  );
};

export { GameContext, GameProvider };
