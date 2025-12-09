// query players hand using api/get-player-hand

import { useQuery, useQueryClient } from "@tanstack/react-query";

export type CardType = {
  card_name: string;
  suit: "r" | "y" | "o" | "b";
  title: string;
  text: string;
  craftable: boolean;
  cost: string[];
  item: string;
  craftedPoints: number;
  ambush: boolean;
  dominance: boolean;
};
// use the token for authentication
const djangoUrl = import.meta.env.VITE_DJANGO_URL;

const useGetPlayerHandQuery = () => {
  const {
    data: playerHand,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: ["player-hand"],
    queryFn: async (): Promise<CardType[]> => {
      const response = await fetch(djangoUrl + "/api/player-hand/", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
          "Content-Type": "application/json",
        },
      });
      return response.json();
    },
  });
  return { playerHand, isLoading, isError, isSuccess };
};

export default useGetPlayerHandQuery;
