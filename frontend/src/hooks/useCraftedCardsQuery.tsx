import { useQuery } from "@tanstack/react-query";
import type { CardType } from "./useGetPlayerHandQuery";

export type CraftedCardData = {
  card: CardType;
  can_be_used: boolean;
  used: boolean;
  action_endpoint: string | null;
};

const djangoUrl = import.meta.env.VITE_DJANGO_URL;

const useCraftedCardsQuery = (gameId: number, faction: string) => {
  const {
    data: craftedCards,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: ["crafted-cards", gameId, faction],
    queryFn: async (): Promise<CraftedCardData[]> => {
      const response = await fetch(
        `${djangoUrl}/api/crafted-cards/${gameId}/${faction}/`,
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
    enabled: !!gameId && !!faction,
  });

  return { craftedCards, isLoading, isError, isSuccess };
};

export default useCraftedCardsQuery;
