import { createContext, useState } from "react";
import type { ReactNode } from "react";
import { useGameSession } from "../hooks/useGames";

const GameContext = createContext<any>({});

const GameProvider = ({ children }: { children: ReactNode }) => {
  const [gameId, setGameId] = useState<number | null>(null);
  const { data: session } = useGameSession(gameId);

  const isGameStarted = session?.status !== "0" && !!session; // "0" is NOT_STARTED

  return (
    <GameContext.Provider
      value={{
        gameId,
        setGameId,
        session,
        isGameStarted,
      }}
    >
      {children}
    </GameContext.Provider>
  );
};

export { GameContext, GameProvider };
