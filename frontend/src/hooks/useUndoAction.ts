import { useMutation, useQueryClient } from "@tanstack/react-query";

const djangoUrl = import.meta.env.VITE_DJANGO_URL;

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
      // Invalidate all queries to refresh state since we traveled back in time
      queryClient.invalidateQueries();
    },
    onError: (error) => {
      console.error("Undo failed:", error);
    },
  });

  return { undoMutation };
};
