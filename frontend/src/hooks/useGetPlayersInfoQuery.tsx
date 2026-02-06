import { useQuery } from "@tanstack/react-query";

export type Player = {
  username: string;
  faction: "ca" | "bi" | "wa";
  faction_label: "Cats" | "Birds" | "Woodland Alliance";
  score: number;
  turn_order: number;
  card_count: number;
};

const useGetPlayersInfoQuery = (gameId: number, enabled: boolean = true) => {
  const {
    data: players,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: ["players", gameId],
    queryFn: async (): Promise<Player[]> => {
      const response = await fetch(
        `${import.meta.env.VITE_DJANGO_URL}/api/players/${gameId}/`,
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
