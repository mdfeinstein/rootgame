import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

const djangoUrl = import.meta.env.VITE_DJANGO_URL;

export type RouteData = {
  route: string;
};
export type StepPayload = {
  type: string;
  name: string;
  value: number | string | boolean | null;
};

export type Option = {
  label: string;
  value: string;
};

export type GameActionStep = {
  faction: string;
  name: string;
  prompt: string;
  endpoint: string;
  payload_details: StepPayload[];
  accumulated_payload: StepPayload[];
  options?: Option[];
};

const useGameActionQuery = (gameId: number, enabled: boolean = true) => {
  const queryClient = useQueryClient();

  const {
    data: actionRoute,
    isLoading: actionRouteIsLoading,
    isError: actionRouteIsError,
    isSuccess: actionRouteIsSuccess,
  } = useQuery({
    queryKey: ["current-action", gameId],
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
  } = useQuery({
    queryKey: ["current-action-info", gameId, actionRoute?.route ?? null],
    queryFn: async (): Promise<GameActionStep> => {
      const response = await fetch(
        `${djangoUrl}${actionRoute?.route}?game_id=${gameId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
          },
        },
      ).then((r) => r.json());
      console.log("action info", response);
      return response;
    },
    enabled: !!actionRoute?.route && enabled,
  });

  const [error, setError] = useState<string | null>(null);
  const submitPayloadMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      // add accumulated payload to payload
      payload = { ...actionInfo?.accumulated_payload, ...payload };

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
      setError(null);
      if (data.name === "completed") {
        // game state has changed. invalidate all queries
        // will also cause a refetch of the current action
        await queryClient.invalidateQueries();
        return;
      }
      //update actionInfo
      queryClient.setQueryData(
        ["current-action-info", gameId, actionRoute?.route ?? null],
        data,
      );
      console.log("success", data);
    },
    onError: (error) => {
      console.log("error", error);
      setError(error.message);
    },
  });

  const cancelProcess = async () => {
    await queryClient.invalidateQueries({
      queryKey: ["current-action", gameId],
    });
    await queryClient.invalidateQueries({
      queryKey: ["current-action-info", gameId],
    });
  };

  const startActionOverride = (route: string) => {
    queryClient.setQueryData(["current-action", gameId], { route });
  };

  return {
    baseEndpoint: actionRoute?.route,
    actionInfo,
    error,
    isLoading: actionInfoIsLoading || actionRouteIsLoading,
    isError: actionInfoIsError || actionRouteIsError,
    isSuccess: actionInfoIsSuccess && actionRouteIsSuccess,
    submitPayloadMutation,
    cancelProcess,
    startActionOverride,
  };
};

export default useGameActionQuery;
