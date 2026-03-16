import { useQuery } from "@tanstack/react-query";
import { gameKeys } from "../api/queryKeys";

const apiUrl = import.meta.env.VITE_API_URL || "/api";

import type { components } from "../api/types";

export type ClearingData = components["schemas"]["Clearing"];

export const useClearingsQuery = (gameId: number, enabled: boolean = true) => {
  return useQuery<ClearingData[]>({
    queryKey: gameKeys.clearings(gameId),
    queryFn: async () => {
      const response = await fetch(`${apiUrl}/clearings/${gameId}/`);
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    },
    enabled: !!gameId && enabled,
  });
};
