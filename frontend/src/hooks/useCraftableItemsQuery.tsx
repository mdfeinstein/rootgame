import { useQuery } from "@tanstack/react-query";
import type { components } from "../api/types";
import { gameKeys } from "../api/queryKeys";

export type CraftableItemType = components["schemas"]["CraftableItem"];
const djangoUrl = import.meta.env.VITE_DJANGO_URL || "";

const useCraftableItemsQuery = (gameId: number, enabled: boolean = true) => {
  const {
    data: craftableItems,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: gameKeys.craftableItems(gameId),
    queryFn: async (): Promise<CraftableItemType[]> => {
      const response = await fetch(`${djangoUrl}/api/craftable-items/${gameId}/`, {
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
  return { craftableItems, isLoading, isError, isSuccess };
};

export default useCraftableItemsQuery;
