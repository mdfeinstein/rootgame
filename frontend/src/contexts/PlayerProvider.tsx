import { createContext, useContext } from "react";
import { GameContext } from "./GameProvider";
import { type FactionLabel } from "../utils/factionUtils";
import { useQuery } from "@tanstack/react-query";
import { UserContext } from "./UserProvider";

import type { components } from "../api/types";

export type PlayerPublic = components["schemas"]["PlayerPublic"];

const PlayerContext = createContext<{
  faction: FactionLabel | null;
}>({
  faction: null,
});

const PlayerProvider = ({ children }: { children: React.ReactNode }) => {
  const { gameId } = useContext(GameContext);
  const { username } = useContext(UserContext);
  const apiUrl = import.meta.env.VITE_API_URL || "/api";

  const { data } = useQuery({
    queryKey: ["playerInfo", gameId, username ?? "anonymous"],
    queryFn: async (): Promise<PlayerPublic | null> => {
      if (!gameId) return null;
      const res = await fetch(`${apiUrl}/player/${gameId}/`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
        },
      });
      if (!res.ok) {
        // Handle error or return null
        return null;
      }
      return res.json();
    },
    enabled: !!gameId,
  });

  const faction = data?.faction?.label || null;

  return (
    <PlayerContext.Provider value={{ faction }}>
      {children}
    </PlayerContext.Provider>
  );
};

export { PlayerContext, PlayerProvider };
