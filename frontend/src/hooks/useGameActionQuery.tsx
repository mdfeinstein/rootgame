import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

const apiUrl = import.meta.env.VITE_API_URL;
const djangoUrl = import.meta.env.VITE_DJANGO_URL;

export type RouteData = {
  route: string;
};
export type StepPayload = {
  type: string;
  name: string;
  value: number | string | boolean | null;
};

export type GameActionStep = {
  faction: string;
  name: string;
  prompt: string;
  endpoint: string;
  payload_details: StepPayload[];
  accumulated_payload: StepPayload[];
};

const useGameActionQuery = (gameId: number) => {
  const queryClient = useQueryClient();
  const signIn = useMutation({
    mutationFn: async (loginData: { username: string; password: string }) => {
      const response = await fetch(`${djangoUrl}/api/token/`, {
        method: "POST",
        // credentials: "include",
        body: JSON.stringify({
          username: loginData.username,
          password: loginData.password,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      });
      return response.json();
    },
    onSuccess: async (data) => {
      localStorage.setItem("accessToken", data.access);
      localStorage.setItem("refreshToken", data.refresh);
      console.log("success", data);
    },
    onError: (error) => {
      console.log("error", error);
    },
  });
  // temporary user sign in here for dev testing
  // useEffect(() => {
  //   signIn.mutate({ username: "user2", password: "password" });
  // }, []);

  const {
    data: actionRoute,
    isLoading: actionRouteIsLoading,
    isError: actionRouteIsError,
    isSuccess: actionRouteIsSuccess,
    dataUpdatedAt: actionRouteDataUpdatedAt,
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
        }
      );
      return response.json();
    },
  });

  const {
    data: actionInfo,
    isLoading: actionInfoIsLoading,
    isError: actionInfoIsError,
    isSuccess: actionInfoIsSuccess,
  } = useQuery({
    queryKey: [
      "current-action-info",
      gameId,
      actionRoute?.route ?? null,
      actionRouteDataUpdatedAt,
    ],
    queryFn: async (): Promise<GameActionStep> => {
      const response = await fetch(
        `${djangoUrl}/${actionRoute?.route}?game_id=${gameId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
          },
        }
      ).then((r) => r.json());
      console.log("action info", response);
      return response;
    },
    enabled: !!actionRoute?.route,
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
        }
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
        // get the next action and its first step
        // await queryClient.invalidateQueries({
        //   queryKey: ["current-action", gameId],
        // });
        // await queryClient.invalidateQueries({
        //   queryKey: ["current-action-info", gameId],
        // });
        await queryClient.invalidateQueries();
        return;
      }
      //update actionInfo
      queryClient.setQueryData(
        [
          "current-action-info",
          gameId,
          actionRoute?.route ?? null,
          actionRouteDataUpdatedAt,
        ],
        data
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

  return {
    baseEndpoint: actionRoute?.route,
    actionInfo,
    error,
    isLoading: actionInfoIsLoading,
    isError: actionInfoIsError,
    isSuccess: actionInfoIsSuccess,
    submitPayloadMutation,
    cancelProcess,
  };
};

export default useGameActionQuery;
