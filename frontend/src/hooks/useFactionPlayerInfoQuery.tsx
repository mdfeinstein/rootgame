import type { UseQueryOptions } from "@tanstack/react-query";
import type { Faction } from "../data/frontend_types";

const apiUrl = import.meta.env.VITE_API_URL;

export const getFactionPlayerInfoQueryOptions = (
  gameId: number,
  faction: Faction,
  enabled: boolean = true,
): UseQueryOptions<any, Error> => ({
  queryKey: ["factionPlayerInfo", gameId, faction.toUpperCase()],
  queryFn: async () => {
    const response = await fetch(
      `${apiUrl}/${faction.toLowerCase()}/player-info/${gameId}/`,
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch player info for ${faction}`);
    }
    return response.json();
  },
  enabled: !!gameId && enabled,
});
