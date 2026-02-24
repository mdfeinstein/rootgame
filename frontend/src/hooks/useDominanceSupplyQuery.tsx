import { useQuery } from "@tanstack/react-query";

const apiUrl = import.meta.env.VITE_API_URL;

export const useDominanceSupplyQuery = (
  gameId: number,
  enabled: boolean = true,
) => {
  const result = useQuery({
    queryKey: ["dominance-supply", gameId],
    queryFn: async () => {
      const response = await fetch(apiUrl + `/dominance-supply/${gameId}/`);
      return response.json();
    },
    enabled: !!gameId && enabled,
  });

  return result;
};
