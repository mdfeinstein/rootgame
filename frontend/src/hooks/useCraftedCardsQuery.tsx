import { useQuery } from "@tanstack/react-query";
import { gameKeys, type FactionValue } from "../api/queryKeys";
import type { CardType } from "./useGetPlayerHandQuery";

export type CraftedCardData = {
  card: CardType;
  can_be_used: boolean;
  used: boolean;
  action_endpoint: string | null;
};

const djangoUrl = import.meta.env.VITE_DJANGO_URL;

const useCraftedCardsQuery = (
  gameId: number,
  faction: FactionValue | undefined,
) => {
  const {
    data: craftedCards,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: gameKeys.craftedCards(gameId, faction as FactionValue),
    queryFn: async (): Promise<CraftedCardData[]> => {
      // Safety mapping: ensure we use the standardized route name even if a stub is passed
      const routeSegments: Record<string, string> = {
        wa: "woodland-alliance",
        ca: "cats",
        bi: "birds",
        cr: "crows",
      };
      const route =
        faction && routeSegments[faction.toLowerCase()]
          ? routeSegments[faction.toLowerCase()]
          : faction;

      if (faction && faction.toLowerCase() in routeSegments) {
        console.warn(
          `[useCraftedCardsQuery] Received short faction code "${faction}". Standardizing to "${route}". Please update caller.`,
        );
      }

      const response = await fetch(
        `${djangoUrl}/api/crafted-cards/${gameId}/${route}/`,
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
