import { useQuery } from "@tanstack/react-query";
import { gameKeys } from "../api/queryKeys";

const apiUrl = import.meta.env.VITE_API_URL || "/api";

export const useDominanceSupplyQuery = (
  gameId: number,
  enabled: boolean = true,
) => {
  const result = useQuery({
    queryKey: gameKeys.dominanceSupply(gameId),
    queryFn: async () => {
      const response = await fetch(apiUrl + `/dominance-supply/${gameId}/`);
      return response.json();
    },
    enabled: !!gameId && enabled,
  });

  return result;
};
