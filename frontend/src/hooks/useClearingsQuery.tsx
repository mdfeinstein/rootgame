import { useQuery } from "@tanstack/react-query";

const apiUrl = import.meta.env.VITE_API_URL;

export interface ClearingData {
  suit_name: string;
  suit: string;
  clearing_number: number;
  connected_to: number[];
  water_connected_to: number[];
  ruins: number[];
}

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
