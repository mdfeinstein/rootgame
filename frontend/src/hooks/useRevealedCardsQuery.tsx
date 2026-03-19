import { useQuery } from "@tanstack/react-query";
import type { components } from "../api/types";
import { gameKeys } from "../api/queryKeys";

export type RevealedCard = components["schemas"]["RevealedCard"];

// fallback for when env var is undefined during test/build
const djangoUrl = import.meta.env.VITE_DJANGO_URL || "";

const useRevealedCardsQuery = (gameId: number, enabled: boolean = true) => {
  const {
    data: revealedCards,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: gameKeys.revealedCards(gameId),
    queryFn: async (): Promise<RevealedCard[]> => {
      const response = await fetch(
        `${djangoUrl}/api/game/revealed-cards/${gameId}/`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
            "Content-Type": "application/json",
          },
        },
      );
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    },
    enabled: !!gameId && enabled,
  });
  return { revealedCards, isLoading, isError, isSuccess };
};

export default useRevealedCardsQuery;
