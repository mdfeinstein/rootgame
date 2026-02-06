// query players hand using api/get-player-hand

import { useQuery, useQueryClient } from "@tanstack/react-query";

type SuitLabel = "Mouse" | "Fox" | "Rabbit" | "Bird";

export type CardType = {
  card_name: string;
  suit: "r" | "y" | "o" | "b";
  suit_name: SuitLabel;
  title: string;
  text: string;
  craftable: boolean;
  cost?: SuitLabel[];
  item?: string;
  item_name?: string;
  crafted_points: number;
  ambush: boolean;
  dominance: boolean;
};
// use the token for authentication
const djangoUrl = import.meta.env.VITE_DJANGO_URL;

const useGetPlayerHandQuery = (
  gameId: number,
  username: string,
  enabled: boolean = true,
) => {
  const {
    data: playerHand,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: ["player-hand", gameId, username],
    queryFn: async (): Promise<CardType[]> => {
      const response = await fetch(`${djangoUrl}/api/player-hand/${gameId}/`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
          "Content-Type": "application/json",
        },
      });
      return response.json();
    },
    enabled: !!gameId && !!username && enabled,
  });
  return { playerHand, isLoading, isError, isSuccess };
};

export default useGetPlayerHandQuery;
