import { useQuery } from "@tanstack/react-query";

import type { components } from "../api/types";

export type PlayerData = components["schemas"]["PlayerPublic"];

const useGetPlayerQuery = (gameId: number, username: string) => {
  const {
    data: player,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: ["player", gameId, username],
    queryFn: async (): Promise<PlayerData> => {
      const response = await fetch(
        `${import.meta.env.VITE_DJANGO_URL}/api/player/${gameId}/`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
            "Content-Type": "application/json",
          },
        },
      );
      return response.json();
    },
    enabled: !!gameId && !!username,
  });
  return { player, isLoading, isError, isSuccess };
};

export default useGetPlayerQuery;
