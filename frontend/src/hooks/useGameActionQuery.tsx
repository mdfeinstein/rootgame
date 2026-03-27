import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useContext } from "react";
import type { components } from "../api/types";
import { gameKeys } from "../api/queryKeys";
import { UserContext } from "../contexts/UserProvider";

const djangoUrl = import.meta.env.VITE_DJANGO_URL || "";

export type RouteData = components["schemas"]["CurrentAction"];
export type GameActionStep = components["schemas"]["GameActionStep"];
export type Option = components["schemas"]["Option"];

const useGameActionQuery = (gameId: number, enabled: boolean = true) => {
  const queryClient = useQueryClient();
  const { username } = useContext(UserContext);

  const {
    data: actionRoute,
    isLoading: actionRouteIsLoading,
    isError: actionRouteIsError,
    isSuccess: actionRouteIsSuccess,
    error: actionRouteError,
  } = useQuery({
    queryKey: gameKeys.currentAction(gameId),
    queryFn: async (): Promise<RouteData> => {
      const response = await fetch(
        djangoUrl + `/api/game/current-action/${gameId}/`,
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

  const {
    data: actionInfo,
    isLoading: actionInfoIsLoading,
    isError: actionInfoIsError,
    isSuccess: actionInfoIsSuccess,
    error: actionInfoError,
  } = useQuery({
    queryKey: gameKeys.currentActionInfo(gameId, actionRoute?.route ?? null, username),
    queryFn: async (): Promise<GameActionStep> => {
      const response = await fetch(
        `${djangoUrl}${actionRoute?.route}?game_id=${gameId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
          },
        },
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to load action info");
      }
      return data;
    },
    enabled: !!actionRoute?.route && enabled && !!username,
    retry: false, // Don't retry on 400 errors usually
  });

  const [mutationError, setMutationError] = useState<string | null>(null);
  
  // Unified error from either the GET query or the POST mutation
  let unifiedError: string | null = mutationError;
  if (actionInfoError instanceof Error) {
    unifiedError = actionInfoError.message;
  } else if (actionRouteError instanceof Error) {
    unifiedError = actionRouteError.message;
  }
  const submitPayloadMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      // add accumulated payload to payload
      payload = {
        ...(actionInfo?.accumulated_payload as Record<string, unknown>),
        ...payload,
      };

      const response = await fetch(
        `${djangoUrl}${actionRoute?.route}${gameId}/${actionInfo?.endpoint}/`,
        {
          method: "POST",
          body: JSON.stringify(payload),
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
            "Content-Type": "application/json",
          },
        },
      );
      if (!response.ok) {
        const error = await response.json();
        if (error.detail) {
          throw new Error(error.detail);
        } else {
          throw new Error(error);
        }
      }

      return response.json();
    },
    onSuccess: async (data) => {
      setMutationError(null);
      if (data.name === "completed") {
        const isWsAuthenticated = queryClient.getQueryData(
          gameKeys.wsAuth(gameId?.toString() || ""),
        );

        if (!isWsAuthenticated) {
          // game state has changed. invalidate all queries if WS is down
          // will also cause a refetch of the current action
          await queryClient.invalidateQueries();
        } else {
          console.log(
            "Action completed. Awaiting WebSocket 'update' instruction to refresh.",
          );
        }
        return;
      }
      //update actionInfo
      queryClient.setQueryData(
        gameKeys.currentActionInfo(gameId, actionRoute?.route ?? null, username),
        data,
      );
      console.log("success", data);
    },
    onError: (error) => {
      console.log("error", error);
      setMutationError(error.message);
    },
  });

  const cancelProcess = async () => {
    await queryClient.invalidateQueries({
      queryKey: gameKeys.currentAction(gameId),
    });
    await queryClient.invalidateQueries({
      queryKey: gameKeys.currentActionInfos(gameId),
    });
  };

  const startActionOverride = (route: string) => {
    queryClient.setQueryData(gameKeys.currentAction(gameId), { route });
  };

  return {
    baseEndpoint: actionRoute?.route,
    actionInfo,
    error: unifiedError,
    isLoading: actionInfoIsLoading || actionRouteIsLoading,
    isError: actionInfoIsError || actionRouteIsError,
    isSuccess: actionInfoIsSuccess && actionRouteIsSuccess,
    submitPayloadMutation,
    cancelProcess,
    startActionOverride,
  };
};

export default useGameActionQuery;
