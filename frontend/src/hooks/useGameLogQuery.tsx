import { useQuery } from "@tanstack/react-query";
import type { components } from "../api/types";
import { gameKeys } from "../api/queryKeys";

export type GameLogType = components["schemas"]["GameLog"];

const djangoUrl = import.meta.env.VITE_DJANGO_URL || "";

const useGameLogQuery = (
  gameId: number,
  username: string | null | undefined,
  enabled: boolean = true,
) => {
  const {
    data: gameLogs,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: gameKeys.gameLog(gameId, username),
    queryFn: async (): Promise<GameLogType[]> => {
      const response = await fetch(`${djangoUrl}/api/game-log/${gameId}/`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
          "Content-Type": "application/json",
        },
      });
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    },
    enabled: !!gameId && !!username && enabled,
  });
  return { gameLogs, isLoading, isError, isSuccess };
};

export default useGameLogQuery;
