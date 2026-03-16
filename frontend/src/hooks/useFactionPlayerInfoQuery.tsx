import type { UseQueryOptions } from "@tanstack/react-query";
import { gameKeys } from "../api/queryKeys";
import { type FactionValue } from "../utils/factionUtils";

const apiUrl = import.meta.env.VITE_API_URL || "/api";

export const getFactionPlayerInfoQueryOptions = (
  gameId: number,
  faction: FactionValue | undefined,
  enabled: boolean = true,
): UseQueryOptions<any, Error> => ({
  queryKey: gameKeys.faction(gameId, faction as FactionValue),
  queryFn: async () => {
    if (!faction) throw new Error("Faction is required for player info query");

    // Safety mapping: ensure we use the standardized route name even if a stub is passed
    const routeSegments: Record<string, string> = {
      wa: "woodland-alliance",
      ca: "cats",
      bi: "birds",
      cr: "crows",
    };
    const route = routeSegments[faction.toLowerCase()] || faction;

    if (faction.toLowerCase() in routeSegments) {
      console.warn(
        `[useFactionPlayerInfoQuery] Received short faction code "${faction}". Standardizing to "${route}". Please update caller.`,
      );
    }

    const response = await fetch(`${apiUrl}/${route}/player-info/${gameId}/`);
    if (!response.ok) {
      throw new Error(`Failed to fetch player info for ${route}`);
    }
    return response.json();
  },
  enabled: !!gameId && !!faction && enabled,
});
