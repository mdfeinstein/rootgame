import { useQuery } from "@tanstack/react-query";
import type { components } from "../api/types";
import { gameKeys } from "../api/queryKeys";

export type Player = components["schemas"]["PlayerPublic"];

const useGetPlayersInfoQuery = (gameId: number, enabled: boolean = true) => {
  const {
    data: players,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: gameKeys.players(gameId),
    queryFn: async (): Promise<Player[]> => {
      const response = await fetch(
        `${import.meta.env.VITE_DJANGO_URL || ""}/api/players/${gameId}/`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
            "Content-Type": "application/json",
          },
        },
      );
      return response.json();
    },
    enabled: !!gameId && enabled,
  });
  return { players, isLoading, isError, isSuccess };
};

export default useGetPlayersInfoQuery;
