import { createContext, useContext } from "react";
import { GameContext } from "./GameProvider";
import { type Faction } from "../data/frontend_types";
import { useQuery } from "@tanstack/react-query";

type FactionStub = "ca" | "bi" | "wa";

const FactionStubToFaction: Record<FactionStub, Faction> = {
  ca: "Cats",
  bi: "Birds",
  wa: "WA",
};

const PlayerContext = createContext<{ faction: Faction | null }>({
  faction: null,
});

const PlayerProvider = ({ children }: { children: React.ReactNode }) => {
  const { gameId } = useContext(GameContext);
  const apiUrl = import.meta.env.VITE_API_URL;

  const { data } = useQuery({
    queryKey: ["playerInfo", gameId],
    queryFn: async () => {
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

  const faction = FactionStubToFaction[data?.faction as FactionStub] || null;

  return (
    <PlayerContext.Provider value={{ faction }}>
      {children}
    </PlayerContext.Provider>
  );
};

export { PlayerContext, PlayerProvider };
