import { useQuery } from "@tanstack/react-query";
import type { components } from "../api/types";
import { gameKeys } from "../api/queryKeys";

export type CardType = components["schemas"]["Card"];
const djangoUrl = import.meta.env.VITE_DJANGO_URL || "";

const useDiscardPileQuery = (gameId: number, enabled: boolean = true) => {
  const {
    data: discardPile,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: gameKeys.discardPile(gameId),
    queryFn: async (): Promise<CardType[]> => {
      const response = await fetch(`${djangoUrl}/api/discard-pile/${gameId}/`, {
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
    enabled: !!gameId && enabled,
  });
  return { discardPile, isLoading, isError, isSuccess };
};

export default useDiscardPileQuery;
