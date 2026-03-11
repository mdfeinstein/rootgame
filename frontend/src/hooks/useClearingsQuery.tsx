import { useQuery } from "@tanstack/react-query";

const apiUrl = import.meta.env.VITE_API_URL;

import type { components } from "../api/types";

export type ClearingData = components["schemas"]["Clearing"];

export const useClearingsQuery = (gameId: number, enabled: boolean = true) => {
  return useQuery<ClearingData[]>({
    queryKey: ["game", gameId, "clearings"],
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
