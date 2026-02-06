import { useQuery } from "@tanstack/react-query";

const apiUrl = import.meta.env.VITE_API_URL;

export const useTurnInfoQuery = (gameId: number, enabled: boolean = true) => {
  const result = useQuery({
    queryKey: ["turn-info", gameId],
    queryFn: async () => {
      const response = await fetch(apiUrl + `/turn-info/${gameId}/`);
      return response.json();
    },
    enabled: !!gameId && enabled,
  });

  return result;
};
