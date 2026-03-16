import { useMutation, useQueryClient } from "@tanstack/react-query";
import { gameKeys } from "../api/queryKeys";

const djangoUrl = import.meta.env.VITE_DJANGO_URL || "";

export const useUndoAction = (gameId: number) => {
  const queryClient = useQueryClient();

  const undoMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`${djangoUrl}/api/game/undo/${gameId}/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to undo");
      }

      return response.json();
    },
    onSuccess: () => {
      const isWsAuthenticated = queryClient.getQueryData(
        gameKeys.wsAuth(gameId?.toString() || ""),
      );

      if (!isWsAuthenticated) {
        // Invalidate all queries for this game since we traveled back in time
        queryClient.invalidateQueries({ queryKey: gameKeys.gameState(gameId) });
      } else {
        console.log(
          "Undo completed. Awaiting WebSocket 'update' instruction to refresh.",
        );
      }
    },
    onError: (error) => {
      console.error("Undo failed:", error);
    },
  });

  return { undoMutation };
};
