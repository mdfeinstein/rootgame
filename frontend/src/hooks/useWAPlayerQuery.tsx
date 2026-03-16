import { useQuery } from "@tanstack/react-query";
import { gameKeys } from "../api/queryKeys";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";
import { PlayerContext } from "../contexts/PlayerProvider";
import { useContext } from "react";

const apiUrl = import.meta.env.VITE_API_URL || "/api";
const useWAPlayerQuery = (gameId: number) => {
  const {
    data: publicInfo,
    isLoading,
    isError,
    isSuccess,
  } = useQuery(getFactionPlayerInfoQueryOptions(gameId, "woodland-alliance"));
  const { faction } = useContext(PlayerContext);
  const {
    data: privateInfo,
    isLoading: privateInfoLoading,
    isError: privateInfoError,
    isSuccess: privateInfoSuccess,
  } = useQuery({
    queryKey: gameKeys.factionPrivate(gameId, "woodland-alliance"),
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
      return response.json();
    },
    enabled: faction === "Woodland Alliance",
  });
  return {
    publicInfo,
    privateInfo,
    isLoading,
    isError,
    isSuccess,
    privateInfoLoading,
    privateInfoError,
    privateInfoSuccess,
  };
};

export default useWAPlayerQuery;
