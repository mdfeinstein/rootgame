import { createContext, useState, useEffect } from "react";
import type { ReactNode, Dispatch, SetStateAction } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useGameSession } from "../hooks/useGames";
import type { GameListItem } from "../hooks/useGames";
import { initDevConsole } from "../utils/devConsole";

export interface GameContextType {
  gameId: number;
  setGameId: Dispatch<SetStateAction<number | null>>;
  session: GameListItem | undefined;
}

const GameContext = createContext<GameContextType>({} as GameContextType);

const GameProvider = ({ children }: { children: ReactNode }) => {
  const [gameId, setGameId] = useState<number | null>(null);
  const { data: session } = useGameSession(gameId);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (gameId) {
      initDevConsole(queryClient, gameId);
    }
  }, [gameId, queryClient]);

  return (
    <GameContext.Provider
      value={{
        gameId: gameId as number,
        setGameId,
        session,
      }}
    >
      {children}
    </GameContext.Provider>
  );
};

export { GameContext, GameProvider };
