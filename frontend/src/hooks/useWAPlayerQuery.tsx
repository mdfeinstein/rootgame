import { useQuery } from "@tanstack/react-query";
import { gameKeys } from "../api/queryKeys";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";
import { PlayerContext } from "../contexts/PlayerProvider";
import { useContext } from "react";

const apiUrl = import.meta.env.VITE_API_URL || "/api";
const useWAPlayerQuery = (gameId: number, enabled: boolean = true) => {
  const {
    data: publicInfo,
    isLoading,
    isError,
    isSuccess,
  } = useQuery(
    getFactionPlayerInfoQueryOptions(gameId, "woodland-alliance", enabled),
  );
  const { faction } = useContext(PlayerContext);
  const isWA = faction === "Woodland Alliance";

  const {
    data: privateInfo,
    isLoading: privateInfoLoading,
    isError: privateInfoError,
    isSuccess: privateInfoSuccess,
  } = useQuery({
    queryKey: gameKeys.factionPrivate(
      gameId,
      "woodland-alliance",
    ),
    queryFn: async () => {
      const response = await fetch(
        apiUrl + "/woodland-alliance/player-private-info/" + gameId + "/",
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
            "Content-Type": "application/json",
          },
        },
      );
      if (!response.ok) {
        throw new Error("Failed to fetch private info");
      }
      return response.json();
    },
    enabled: enabled && isWA,
  });

  return {
    publicInfo,
    privateInfo,
    isLoading: isLoading || (isWA && privateInfoLoading),
    isError: isError || (isWA && privateInfoError),
    isSuccess,
    privateInfoSuccess,
  };
};

export default useWAPlayerQuery;
