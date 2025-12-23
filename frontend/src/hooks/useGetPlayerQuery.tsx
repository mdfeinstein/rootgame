import { useQuery, useQueryClient } from "@tanstack/react-query";
import { use } from "react";

const useGetPlayerQuery = (gameId: number, username: string) => {
  const {
    data: player,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: ["player", gameId, username],
    queryFn: async (): Promise<{ faction: string }> => {
      const response = await fetch(
        `${import.meta.env.VITE_DJANGO_URL}/api/player/${gameId}/`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
            "Content-Type": "application/json",
          },
        }
      );
      return response.json();
    },
    enabled: !!gameId && !!username,
  });
  return { player, isLoading, isError, isSuccess };
};

export default useGetPlayerQuery;
